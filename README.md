# Ecommerce Backend Application
This application consists of a simple backend application FastAPI, Python and MongoDB. It consists of the following two APIs:
  1. List all products
  2. Create order API


## How to use:
To use the application, clone it and use the following command: uvicorn app:app --reload. On doing this the application will start running and you will have the following two APIs that you can test on postman:
  1. http://127.0.0.1:8000/products
  2. http://127.0.0.1:8000/orders/create


In the get products API, following query parameters can be used for filtering the database:
  1. limit
  2. skip
  3. min_price ( Optional )
  4. max_price ( Optional - max_price should be greater than or equal to min_price otherwise the code is meant to throw an error )

In the create order API, body in the following format is needed along with the followinf constrains:
  1. The productId should exists in the products collection.
  2. The quantity of the products in the order should be less than or equal to the available quantity in products collection.
  3. The address should be valid and should have all three keys in it.
  ```
    {
      "products": [{
        "productId": "65b785503555e34be228d821",
        "quantity": 1
      }],
      "address": {
        "city": "Vadodara",
        "country": "India",
        "zipCode": 390011
      }
  }
  ```


## About Code:
#### Get Products API:
   Get products API function uses an aggregate query with three stages, a project stage to convert _id to id, a match query stage for filtering on the basis of min_price and max_price while the last is a facet stage that implements pagination and gives the page count.

   It has a check if the min_price is greater than max_price then it throws an error since that shouldn't be allowed.

#### Create Order API:
  The create order api functions has a lot of checks which ensures that the data passed in the body is correct. It loops through the entire product list passed and checks if any product is repeated in the array and if it is then it combines the quantity of the two.

  It uses mongo transactions as well to make sure that the Atomicity is maintained in the database.
