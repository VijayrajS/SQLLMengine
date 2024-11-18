import requests
import json

def run_query(question):
    url = "http://127.0.0.1:8000/query"
    headers = {"Content-Type": "application/json"}
    payload = {"question": question}
    
    try:
        # Send POST request
        response = requests.post(url, headers=headers, json=payload)
        
        # Raise an error for bad status codes
        # response.raise_for_status()
    
        # Parse the response JSON
        response_data = response.json()
        
        # Print the response nicely formatted
        print("Response Data:")
        print(json.dumps(response_data, indent=4))
        print(response)

    except requests.exceptions.RequestException as e:
            print(f"Error occurred: {e}")

# Example usage
if __name__ == "__main__":
    question = "Get median and mean household income aggregated for each year."
   # question = "For each area in New York, give count of each crime type."
    question = "Give me number of employees who are male"
   # question = "Retrieve all records from the economic_income_and_benefits table where the mean_household_income is more than 100,000 and the crime classification (Crime_Class) is 'Felony'."
    run_query(question)
