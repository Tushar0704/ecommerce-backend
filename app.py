import certifi
import traceback
from typing import List
from bson import ObjectId
from datetime import datetime
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from fastapi import FastAPI, HTTPException
from pymongo import MongoClient, WriteConcern, ReadPreference, UpdateOne

# Creating a FastAPI instance
app = FastAPI()

# Creating productList model
class productList(BaseModel):
    productId: str
    quantity: int

# Creating address model
class address(BaseModel):
    city: str
    country: str
    zipCode: int

# Creating create Order model
class createOrder(BaseModel):
    address: address
    products: List[productList]

# for SSL certificates.
ca = certifi.where()

# create client for mongo connection.
client = MongoClient()

# connect using the connection string
mongo_client = MongoClient("mongodb+srv://agarwaltushar65:N7spOwiFe4rNUwpc@production-cluster.4txskbt.mongodb.net/ecommerce-app?", tlsCAFile=ca)

# define database and collections.
database = mongo_client["ecommerce-app"]

# define collections
users_collection = database["users"]
orders_collection = database["orders"]
products_collection = database["products"]

# API for getting all products.
@app.get("/products")
def get_all_products(skip: int = 0, limit: int = 10, min_price: int | None = None, max_price: int | None = None ):
    try:
        # Create an aggregation pipeline to get all products.
        pipeline = [{ "$project": { "_id": 0, "id": {"$toString": "$_id"}, "name": 1, "price": 1, "quantity": 1 } }, { "$facet": { "data": [{"$skip": skip}, {"$limit": limit}], "page": [{"$count": "total"}] } }]

        # If both min_price and max_price are provided, add a match stage to the pipeline.
        if min_price and max_price:
            # Check if min_price is greater than max_price.
            if min_price > max_price:
                raise HTTPException(status_code= 400, detail = "min_price should be less than max_price.")

            # Add a match stage to the pipeline.
            pipeline.insert(0, {"$match": {"price": {"$gte": min_price, "$lte": max_price}}})
        elif min_price:
            pipeline.insert(0, {"$match": {"price": {"$gte": min_price}}})
        elif max_price:
            pipeline.insert(0, {"$match": {"price": {"$lte": max_price}}})

        # Execute the aggregation pipeline and fetch the data.
        products_data = list(products_collection.aggregate(pipeline))

        # return the response with a 200 status code.
        return {"statusCode": 200, "data": products_data}

    except Exception as e:
        # Print the traceback information of the error.
        traceback_info = traceback.format_exc()
        print("Traceback Information:", traceback_info)

        # returning a 500 error response to the client.
        raise HTTPException(status_code= 500, detail = "Error while fetching products data.")
    

# API to create a new product.
@app.post("/orders/create")
def create_order(order: createOrder):
    try:
        # Initializing the total price of the order.
        total_amount = 0

        # Initializing products list.
        combined_products = []

        # Initializing the bulk operations list.
        bulk_operations = []

        # Checking if the address is valid.
        if not order.address or not order.address.city or not order.address.country or not order.address.zipCode:
            raise HTTPException(status_code= 400, detail = "Please provide a valid address.")
        
        # Checking if the products list is empty.
        if not order.products:
            raise HTTPException(status_code= 400, detail = "Please provide at least one product.")
        
        # Looping through the products list and creating a new list that contains the products with their quantity.
        for product in order.products:
            # Checking if the product id is valid.
            if not product.productId:
                raise HTTPException(status_code= 400, detail = "Please provide a valid product id.")
            
            # Checking if the quantity is valid.
            if not product.quantity or product.quantity <= 0:
                raise HTTPException(status_code= 400, detail = "Please provide a valid quantity.")
            
            # if the product already exists in the products list, then increment the quantity.
            if any(product["productId"] == combined_product["productId"] for combined_product in combined_products):
                [product["quantity"] + combined_product["quantity"] for combined_product in combined_products if product["productId"] == combined_product["productId"]]
                continue
            else:
                # Adding the product to the products list.
                combined_products.append({"productId": product.productId, "quantity": product.quantity})
                    
        # Getting the product details from the product collection.
        pipeline = [{"$match": {"_id": {"$in": [ObjectId(combined_product["productId"]) for combined_product in combined_products]}}}, {"$project": {"_id": 0, "id": { "$toString": "$_id" }, "name": 1, "price": 1, "quantity": 1}}]

        products_data = list(products_collection.aggregate(pipeline))

        # Checking if all the products are available.
        if len(products_data) != len(combined_products):
            raise HTTPException(status_code= 400, detail = "One or more products are not available.")

        # Checking if the product exists or not; if the total number of each product is less than the quantity ordered;
        for product in products_data:
            # Check if the total number of each product is less than the quantity ordered.
            if product["quantity"] < [combined_product["quantity"] for combined_product in combined_products if combined_product["productId"] == product["id"]][0]:
                raise HTTPException(status_code= 400, detail = f"Total number of {product['name']} available is less than the quantity ordered.")

            # Adding the update_one operation to the bulk_operations list.
            bulk_operations.append(UpdateOne({"_id": ObjectId(product["id"])}, {"$inc": {"quantity": -[combined_product["quantity"] for combined_product in combined_products if combined_product["productId"] == product["id"]][0]}}))

            # Calculating the total amount of the order.
            total_amount += product["price"] * [combined_product["quantity"] for combined_product in combined_products if combined_product["productId"] == product["id"]][0]
        
        # Creating a transaction to add the order details to the orders collection and update the quantity of the products.
        wc_majority = WriteConcern("majority", wtimeout=1000)
        
        # Creating a transaction to add the order details to the orders collection and update the quantity of the products.
        def complete_order(session):
            # Adding the order details to the orders collection.
            orders_collection.insert_one({"address": dict(order.address), "products": list(combined_products), "totalAmount": total_amount, "created_at": datetime.now().isoformat()}, session=session)

            # Updating the quantity of the products.
            products_collection.bulk_write(bulk_operations, session=session)

        # Starting a transaction.
        with mongo_client.start_session() as session:
            # Using with_transaction to start a transaction, execute the callback, and commit (or abort on error).
            session.with_transaction(complete_order, write_concern=wc_majority, read_preference=ReadPreference.PRIMARY)

            # Return the response with a 200 status code.
            return {"status_code": 200, "message": "Order placed successfully."}

    except Exception as e:
        # Print the traceback information of the error.
        traceback_info = traceback.format_exc()
        print("Traceback Information:", traceback_info)

        return e
