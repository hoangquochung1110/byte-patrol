def create_request_counter():
    request_count = 0
    
    def make_request(url, params=None):
        nonlocal request_count
        request_count += 1
        
        print(f"Making request #{request_count} to {url}")
        # Here you would actually make the HTTP request
        # For example: response = requests.get(url, params=params)
        
        # For demonstration, just return a simulated response
        return {
            "status": 200,
            "request_number": request_count,
            "url": url,
            "params": params
        }
    
    return make_request

# Create a counter for a specific API service
weather_api = create_request_counter()
stock_api = create_request_counter()

# Each counter maintains its own state
response1 = weather_api("https://api.weather.com/forecast", {"city": "New York"})
response2 = stock_api("https://api.stocks.com/quote", {"symbol": "AAPL"})
response3 = weather_api("https://api.weather.com/current", {"city": "London"})

print(f"Weather API has made {response3['request_number']} requests")
print(f"Stock API has made {response2['request_number']} requests")