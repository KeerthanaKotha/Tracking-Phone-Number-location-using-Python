
from flask import Flask, request, render_template, jsonify
import phonenumbers
from phonenumbers import geocoder, carrier
import folium
from opencage.geocoder import OpenCageGeocode
import threading
import time
import os

app = Flask(__name__)

# Initialize OpenCageGeocode with your API key
geocoder_key = "ca4b6651d5ab4fe994f1b1df064e4039"
geocoder_instance = OpenCageGeocode(geocoder_key)

# To store locations globally
locations = {}
tracking_info = []

def get_location_info(number):
    try:
        check_number = phonenumbers.parse(number)
        number_location = geocoder.description_for_number(check_number, "en")
        service_provider = carrier.name_for_number(check_number, "en")
        return number_location, service_provider
    except phonenumbers.phonenumberutil.NumberParseException:
        return None, None

def get_coordinates(location, geocoder_instance):
    query = str(location)
    results = geocoder_instance.geocode(query)
    if results:
        lat = results[0]['geometry']['lat']
        lng = results[0]['geometry']['lng']
        return lat, lng
    else:
        return None, None

def plot_on_map(locations, output_file):
    map_location = folium.Map(location=[0, 0], zoom_start=2)

    for loc, info in locations.items():
        lat, lng = info['coordinates']
        popup_info = f"Location: {info['region']}<br>Service Provider: {info['service_provider']}"
        folium.Marker([lat, lng], popup=popup_info).add_to(map_location)

    map_location.save(output_file)

def track_real_time(numbers, geocoder_instance, output_file):
    global tracking_info
    local_locations = {}
    tracking_info = []
    for number in numbers:
        number_location, service_provider = get_location_info(number)
        if number_location:
            lat, lng = get_coordinates(number_location, geocoder_instance)
            if lat and lng:
                local_locations[number] = {
                    'region': number_location,
                    'service_provider': service_provider,
                    'coordinates': (lat, lng)
                }
                tracking_info.append(f"Number: {number}<br>Region: {number_location}<br>Latitude: {lat}<br>Longitude: {lng}<br>Service Provider: {service_provider}<br>--------------------------<br>")
    
    locations.update(local_locations)
    plot_on_map(locations, output_file)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        numbers = request.form.get('numbers').split(',')
        output_file = "static/mylocations.html"
        tracking_thread = threading.Thread(target=track_real_time, args=(numbers, geocoder_instance, output_file))
        tracking_thread.daemon = True
        tracking_thread.start()
        time.sleep(2)  # Give the thread some time to gather initial data
        return jsonify({"status": "Tracking started", "map_url": output_file, "details": "<br>".join(tracking_info)})

    return render_template('index.html')

@app.route('/map')
def map_view():
    return render_template('map.html')

if __name__ == "__main__":
    if not os.path.exists('static'):
        os.makedirs('static')
    app.run(debug=True)
