# Terry Almeida
# This program searches for flexible car rental rates based on the pick-up and drop-off times and dates
import requests
import json
import datetime as dt
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
from prettytable import PrettyTable

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


def check_alternative_dates(
        token, original_pickup_date, pickup_time, pickup_location,
        original_dropoff_date, dropoff_time, dropoff_location, country_code, brand='Avis'
):
    # Convert string dates to datetime objects
    pickup_date = datetime.strptime(original_pickup_date, "%Y-%m-%d")
    dropoff_date = datetime.strptime(original_dropoff_date, "%Y-%m-%d")

    # Calculate alternative dates
    dates = [
        (pickup_date + timedelta(days=offset), dropoff_date + timedelta(days=offset))
        for offset in [-1, 0, 1]
    ]

    results = {}
    for (new_pickup_date, new_dropoff_date) in dates:
        formatted_pickup_date = new_pickup_date.strftime("%Y-%m-%d")
        formatted_dropoff_date = new_dropoff_date.strftime("%Y-%m-%d")

        availability = get_car_availability(
            token, formatted_pickup_date, pickup_time, pickup_location,
            formatted_dropoff_date, dropoff_time, dropoff_location, country_code, brand
        )
        if availability:
            key = f"Pickup: {formatted_pickup_date}, Dropoff: {formatted_dropoff_date}"
            results[key] = availability
        else:
            print(f"Failed to retrieve availability for {formatted_pickup_date} to {formatted_dropoff_date}")

    return results


def display_lowest_prices(alternative_availabilities):
    # Structure to hold the lowest prices for each combination of date and vehicle class
    lowest_prices = defaultdict(lambda: defaultdict(lambda: float('inf')))

    # Extract the relevant data
    for date_key, availability in alternative_availabilities.items():
        pickup_date, dropoff_date = date_key.replace("Pickup: ", "").split(", Dropoff: ")
        for vehicle in availability.get('vehicles', []):
            vehicle_class = vehicle['category']['vehicle_class_name']
            total_price = vehicle['rate_totals']['pay_later']['reservation_total']
            if total_price < lowest_prices[pickup_date][vehicle_class]:
                lowest_prices[pickup_date][vehicle_class] = total_price
            if total_price < lowest_prices[dropoff_date][vehicle_class]:
                lowest_prices[dropoff_date][vehicle_class] = total_price

    # Convert dictionary to DataFrame for better formatting
    price_df = pd.DataFrame(lowest_prices).T
    price_df.index.name = 'Date'
    price_df.columns.name = 'Vehicle Class'

    # Print the DataFrame in a more readable table format
    print(price_df.fillna('-').to_string())


def format_alternative_date(date_str, offset):
    date = dt.datetime.strptime(date_str, "%Y-%m-%d")
    new_date = date + dt.timedelta(days=offset)
    return new_date.strftime("%Y-%m-%d")


def gather_alternative_availabilities(access_token, base_pickup_date, pickup_time, location_code, base_dropoff_date,
                                      dropoff_time, country_code):
    dates_info = defaultdict(lambda: defaultdict(lambda: (float('inf'), "")))
    for pd_offset in range(-1, 2):  # -1, 0, +1 for pickup
        for dd_offset in range(-1, 2):  # -1, 0, +1 for dropoff
            pickup_date = format_alternative_date(base_pickup_date, pd_offset)
            dropoff_date = format_alternative_date(base_dropoff_date, dd_offset)
            availability = get_car_availability(access_token, pickup_date, pickup_time, location_code, dropoff_date,
                                                dropoff_time, location_code, country_code)
            if availability and 'vehicles' in availability:
                for vehicle in availability['vehicles']:
                    price = vehicle['rate_totals']['pay_later']['reservation_total']
                    if price < dates_info[pickup_date][dropoff_date][0]:
                        dates_info[pickup_date][dropoff_date] = (price, vehicle['category']['vehicle_class_name'])
    return dates_info


# def print_price_table(dates_info):
#     pickup_dates = sorted({key for key in dates_info})
#     dropoff_dates = sorted({key for date_dict in dates_info.values() for key in date_dict})
#
#     table = PrettyTable()
#     table.field_names = ["Dropoff / Pickup"] + pickup_dates + [""]
#
#     for dropoff_date in dropoff_dates:
#         row = [dropoff_date]
#         for pickup_date in pickup_dates:
#             price, v_class = dates_info[pickup_date][dropoff_date]
#             row.append(f"${price} ({v_class})" if v_class else "N/A")
#         row.append(dropoff_date)
#         table.add_row(row)
#
#     print(table)

# def print_price_table(dates_info):
#     pickup_dates = sorted({key for key in dates_info})
#     dropoff_dates = sorted({key for date_dict in dates_info.values() for key in date_dict})
#
#     table = PrettyTable()
#     # Adjust field names to only include dropoff date in the last column
#     table.field_names = ["Dropoff / Pickup"] + pickup_dates + ["Dropoff Dates"]
#
#     for dropoff_date in dropoff_dates:
#         row = [dropoff_date]
#         for pickup_date in pickup_dates:
#             # Safely get the price and class if exists, otherwise mark as "N/A"
#             price_class = dates_info.get(pickup_date, {}).get(dropoff_date, (None, None))
#             price, v_class = price_class
#             row.append(f"${price} ({v_class})" if price and v_class else "N/A")
#         row.append(dropoff_date)  # Add dropoff date at the end of the row
#         table.add_row(row)
#
#     print(table)


def print_price_table(dates_info):
    pickup_dates = sorted({key for key in dates_info})
    dropoff_dates = sorted({key for date_dict in dates_info.values() for key in date_dict})

    table = PrettyTable()
    table.field_names = ["Pickup / Dropoff"] + pickup_dates

    # Iterate over each dropoff date to create rows
    for dropoff_date in dropoff_dates:
        row = [dropoff_date]
        for pickup_date in pickup_dates:
            # Accessing price and vehicle class tuple, default to "N/A" if not found
            price_class = dates_info.get(pickup_date, {}).get(dropoff_date, ("N/A", ""))
            price, v_class = price_class
            # Format cell as "price (class)" if both price and class are available
            row.append(f"${price} ({v_class})" if price != "N/A" else "N/A")
        table.add_row(row)

    print(table)

def main():
    access_token = get_access_token()
    if not access_token:
        print("Failed to retrieve access token.")
        return

    # User inputs
    country_code = 'US'
    keyword = 'Newark'
    locations = get_car_locations(access_token, country_code, keyword)
    if not locations or 'locations' not in locations:
        print("Failed to retrieve locations or no locations found.")
        return

    # for i, location in enumerate(locations['locations']):
    #     print(f"{i+1}: {location.get('name')} ({location.get('code')}) - "
    #           f"{location.get('address', {}).get('address_line_1')}, {location.get('address', {}).get('city')}")
    location_choice = 1
    selected_location = locations['locations'][location_choice]

    pickup_date = '2024-08-10'
    pickup_time = '10:00:00'
    dropoff_date = '2024-08-25'
    dropoff_time = '10:00:00'

    dates_info = gather_alternative_availabilities(
        access_token, pickup_date, pickup_time, selected_location['code'],
        dropoff_date, dropoff_time, country_code
    )

    # Display formatted table of lowest prices
    print_price_table(dates_info)



# def main():
#     access_token = get_access_token()
#     if not access_token:
#         print("Failed to retrieve access token.")
#         return
#     country_code = 'US'
#     keyword = 'Newark'
#
#     # # User inputs for locations
#     # country_code = input("Enter country code (e.g., US): ")
#     # keyword = input("Enter keyword for location search (e.g., Denver): ")
#
#     # Fetch car locations
#
#     locations = get_car_locations(access_token, country_code, keyword)
#     if not locations or 'locations' not in locations:
#         print("Failed to retrieve locations or no locations found.")
#         return
#
#     # Display locations and let user choose
#     for i, location in enumerate(locations['locations']):
#         # Safely get values using .get() method
#         name = location.get('name', 'Unknown name')
#         code = location.get('code', 'Unknown code')
#         address_line_1 = location.get('address', {}).get('address_line_1', 'Unknown address')
#         city = location.get('address', {}).get('city', 'Unknown city')
#         print(f"{i + 1}: {name} ({code}) - {address_line_1}, {city}")
#     location_choice = 1
#     # location_choice = int(input("Choose a location by number: ")) - 1
#     selected_location = locations['locations'][location_choice]
#
#     pickup_date = '2024-08-10'
#     pickup_time = '10:00:00'
#     dropoff_date = '2024-08-25'
#     dropoff_time = '10:00:00'
#
#     # # User inputs for dates and times
#     # pickup_date = input("Enter pickup date (YYYY-MM-DD): ")
#     # pickup_time = input("Enter pickup time (HH:MM:SS): ")
#     # dropoff_date = input("Enter dropoff date (YYYY-MM-DD): ")
#     # dropoff_time = input("Enter dropoff time (HH:MM:SS): ")
#
#     # Fetch car availability and rates using selected location
#
#     availability = get_car_availability(
#         access_token, pickup_date, pickup_time, selected_location['code'],
#         dropoff_date, dropoff_time, selected_location['code'], country_code
#     )
#     if availability:
#         # Initialize summary dictionary
#         summary = {}
#         for vehicle in availability.get('vehicles', []):
#             class_name = vehicle.get('category', {}).get('vehicle_class_name', 'Unknown Class')
#             reservation_total = vehicle.get('rate_totals', {}).get('pay_later', {}).get('reservation_total', 0.0)
#             summary[class_name] = reservation_total
#
#         # Print the summary
#         print("Summary of Reservation Totals by Vehicle Class:")
#         for class_name, total in summary.items():
#             print(f"{class_name}: ${total:.2f}")
#
#         if summary:
#             # Find the minimum reservation total and its associated class name
#             lowest_class_name, lowest_price = min(summary.items(), key=lambda item: item[1])
#             print(f"Lowest Reservation Total: ${lowest_price:.2f} ({lowest_class_name})")
#
#         print("Detailed Car Availability:")
#         print(json.dumps(availability, indent=2))
#     else:
#         print("Failed to retrieve car availability.")
#
#     # rate = get_car_rate(
#     #     access_token, pickup_date, pickup_time, selected_location['code'],
#     #     dropoff_date, dropoff_time, selected_location['code'], country_code
#     # )
#     # if rate:
#     #     print("Car rates:", json.dumps(rate, indent=2))
#     # else:
#     #     print("Failed to retrieve car rates.")


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
