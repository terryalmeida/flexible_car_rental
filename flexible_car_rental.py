# Terry Almeida
# This program searches for flexible car rental rates based on the pick-up and drop-off times and dates
import requests
import json
from datetime import datetime, timedelta

# client id and secret variables
client_id = "eb7c4616"
client_secret = "543b3e145cbc5d76157831805f2ff382"


# api endpoint for access token
def get_access_token():
    url = "https://stage.abgapiservices.com/oauth/token/v1"  # API endpoint for access token
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'client_id': client_id,
        'client_secret': client_secret,
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        token_info = json.loads(response.text)
        token_info['expires_at'] = datetime.now() + timedelta(seconds=token_info['expires_in'])
        return token_info['access_token']
    else:
        print(f"Failed to get access token: {response.text}")
        return None


# get car locations
def get_car_locations(token, country_code, keyword, brand='Avis'):
    url = "https://stage.abgapiservices.com/cars/locations/v1"
    headers = {
        'Authorization': f"Bearer {token}",
        'Accept': 'application/json',
        'client_id': client_id  # Confirm if it needs to be in headers as per the API's current configuration
    }
    params = {
        'brand': brand,
        'country_code': country_code,
        'keyword': keyword
    }
    response = requests.get(url, headers=headers, params=params)
    # print(f"get_car_location response: {response}")
    # print(f"get_car_location request sent to URL: {response.request.url}")  # Debugging statement
    # print(f"get_car_location status code: {response.status_code}")  # Log the status code

    if response.status_code == 200:
        return json.loads(response.text)
    else:
        print(f"Failed to get car locations: {response.text}")
        return None


def get_car_availability(
        token, pickup_date, pickup_time, pickup_location, dropoff_date, dropoff_time, dropoff_location, country_code,
        brand='Avis'
):
    pickup_date_and_time = pickup_date + 'T' + pickup_time
    dropoff_date_and_time = dropoff_date + 'T' + dropoff_time
    url = "https://stage.abgapiservices.com:443/cars/catalog/v1/vehicles"
    headers = {
        'Authorization': f'Bearer {token}',
        'client_id': client_id
    }
    params = {
        'brand': brand,
        'pickup_date': pickup_date_and_time,  # format:'2024-06-01T10:00:00'
        'pickup_location': pickup_location,  # EWR
        'dropoff_date': dropoff_date_and_time,
        'dropoff_location': dropoff_location,
        'country_code': country_code  # US
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get car availability: {response.text}")
        return None


def get_car_rate(
        token, pickup_date, pickup_time, pickup_location, dropoff_date, dropoff_time, dropoff_location,
        country_code='US', brand='Avis', rate_code='G3', vehicle_class_code='A'
):
    pickup_date_and_time = pickup_date + 'T' + pickup_time
    dropoff_date_and_time = dropoff_date + 'T' + dropoff_time
    url = "https://stage.abgapiservices.com:443/cars/catalog/v1/vehicles/rates"
    headers = {
        'Authorization': f'Bearer {token}',
        'client_id': client_id
    }
    params = {
        'brand': brand,
        'country_code': country_code,
        'dropoff_date': dropoff_date_and_time,
        'dropoff_location': dropoff_location,
        'pickup_date': pickup_date_and_time,  # format:'2024-06-01T10:00:00'
        'pickup_location': pickup_location,  # EWR
        'rate_code': rate_code,
        'vehicle_class_code': vehicle_class_code

    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get car rate: {response.text}")
        return None


def main():
    access_token = get_access_token()
    if not access_token:
        print("Failed to retrieve access token.")
        return

    # User inputs for locations
    country_code = input("Enter country code (e.g., US): ")
    keyword = input("Enter keyword for location search (e.g., Denver): ")

    # Fetch car locations
    locations = get_car_locations(access_token, country_code, keyword)
    if not locations or 'locations' not in locations:
        print("Failed to retrieve locations or no locations found.")
        return

    # Display locations and let user choose
    for i, location in enumerate(locations['locations']):
        # Safely get values using .get() method
        name = location.get('name', 'Unknown name')
        code = location.get('code', 'Unknown code')
        address_line_1 = location.get('address', {}).get('address_line_1', 'Unknown address')
        city = location.get('address', {}).get('city', 'Unknown city')
        print(f"{i + 1}: {name} ({code}) - {address_line_1}, {city}")

    location_choice = int(input("Choose a location by number: ")) - 1
    selected_location = locations['locations'][location_choice]

    pickup_date = '2024-12-30'
    pickup_time = '20:00:00'
    dropoff_date = '2024-12-31'
    dropoff_time = '20:00:00'


    # # User inputs for dates and times
    # pickup_date = input("Enter pickup date (YYYY-MM-DD): ")
    # pickup_time = input("Enter pickup time (HH:MM:SS): ")
    # dropoff_date = input("Enter dropoff date (YYYY-MM-DD): ")
    # dropoff_time = input("Enter dropoff time (HH:MM:SS): ")

    # Fetch car availability and rates using selected location
    availability = get_car_availability(
        access_token, pickup_date, pickup_time, selected_location['code'],
        dropoff_date, dropoff_time, selected_location['code'], country_code
    )
    if availability:
        # Initialize summary dictionary
        summary = {}
        for vehicle in availability.get('vehicles', []):
            class_name = vehicle.get('category', {}).get('vehicle_class_name', 'Unknown Class')
            reservation_total = vehicle.get('rate_totals', {}).get('pay_later', {}).get('reservation_total', 0.0)
            summary[class_name] = reservation_total

        # Print the summary
        print("Summary of Reservation Totals by Vehicle Class:")
        for class_name, total in summary.items():
            print(f"{class_name}: ${total:.2f}")

        print("Detailed Car Availability:")
        print(json.dumps(availability, indent=2))
    else:
        print("Failed to retrieve car availability.")

    rate = get_car_rate(
        access_token, pickup_date, pickup_time, selected_location['code'],
        dropoff_date, dropoff_time, selected_location['code'], country_code
    )
    if rate:
        print("Car rates:", json.dumps(rate, indent=2))
    else:
        print("Failed to retrieve car rates.")


if __name__ == "__main__":
    main()






    # FOR TESTING
    # keyword = 'Denver'
    # pickup_date = '2024-12-30'
    # pickup_time = '10:00:00'
    # pickup_location = 'EWR'
    # dropoff_date = '2024-12-31'
    # dropoff_time = '10:00:00'
    # dropoff_location = 'EWR'
    # country_code = 'US'
    #
    # locations = get_car_locations(access_token, country_code, keyword, brand='Avis')
    # availability = get_car_availability(access_token, pickup_date, pickup_time, pickup_location, dropoff_date,
    #                                     dropoff_time, dropoff_location, country_code, brand='Avis')
    # rate = get_car_rate(access_token, pickup_date, pickup_time, pickup_location, dropoff_date, dropoff_time,
    #                     dropoff_location, country_code='US', brand='Avis', rate_code='G3', vehicle_class_code='A')
    #
    # print("Car locations:", locations)
    # print("Car availability:", availability)
    # print("Car rates:", rate)
