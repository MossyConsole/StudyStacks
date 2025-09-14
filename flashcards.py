from flask import Flask, Response, request
import pymongo
import json
from bson.objectid import ObjectId

app = Flask(__name__)

try:
    mongo = pymongo.MongoClient(
        host='localhost', 
        port=27017,
        serverSelectionTimeoutMS = 1000
    )
    db = mongo.studystack
    mongo.server_info() # Triggers the exception if connection to the database is unsuccessful
except:
    print("ERROR - Cannot connect to db")

#==================================#

@app.route("/flashcards", methods=["POST"])
def create_flashcard():
    try:
        flashcard = {
            "id": request.form["id"],
            "question": request.form["question"],
            "answer": request.form["answer"],
            "correct_answers": 0
                }
        dbResponse = db.flashcards.insert_one(flashcard)
        print(dbResponse.inserted_id)
        # for attr in dir(dbResponse):
        #     print(attr)
        return Response(
            response= json.dumps(
                {"message":"flashcard created",
                "id":f"{dbResponse.inserted_id}"
                }),
            status=200, # All okay
            mimetype="application/json"
        )
    except Exception as ex:
        print("******")
        print(ex)
        print("******")
        return Response(
            response = json.dumps({"message":"cannot create flashcard"}),
            status=500, # Internal server error
            mimetype ="application/json"
        )


#==================================#

@app.route("/flashcards", methods=["GET"])
def get_some_flashcards():
    try:
        data = list(db.flashcards.find())
        for question in data:
            question["_id"] = str(question["_id"])
        return Response(
            response = json.dumps(data),
            status=200, # All okay
            mimetype ="application/json"
        )
    except Exception as ex:
        print(ex)
        return Response(
            response = json.dumps({"message":"cannot read flashcards"}),
            status=500, # Internal server error
            mimetype ="application/json"
        )

#==================================#

@app.route("/flashcards/<id>", methods=["PATCH"])
def update_flashcard(id):
    try:
        dbResponse = db.flashcards.update_one(
            {"_id":ObjectId(id)},
            {"$set":{"question":request.form["question"]}}
        )
        # for attr in dir(dbResponse):
        #    print(f"*** {attr} ***")
        if dbResponse.modified_count == 1:
            return Response(
                response = json.dumps({"message": "flashcard updated"}),
                status = 200, # Everything okay
                mimetype = "application/json"
            )
        else:
            return Response(
                response = json.dumps({"message": "nothing to update"}),
                status = 200, # Everything okay
                mimetype ="application/json"
            )
    except Exception as ex:
        return Response(
            response = json.dumps({"message":"cannot update"}),
            status = 500, # Internal server error
            mimetype = "application/json"
        )

#==================================#

@app.route("/flashcards/<id>", methods=["DELETE"])
def delete_flashcard(id):
    try:
        dbResponse = db.flashcards.delete_one({"_id":ObjectId(id)})
        if dbResponse.deleted_count == 1:
            return Response(
            response = json.dumps({
                    "message":"flashcard deleted", "id":f"{id}"}),
            status=200, # Everything okay
            mimetype ="application/json"
            )
        # for attr in dbResponse:
        #    print(f"*** {attr} ***")
        return Response(
            response = json.dumps({
                    "message":"flashcard not found",
                    "id":f"{id}"}),
            status = 200, # Everything okay
            mimetype ="application/json"
        )
    except Exception as ex:
        return Response(
            response = json.dumps({"message":"cannot delete flashcard"}),
            status = 500, # Internal server error
            mimetype = "application/json"
        )

#==================================#

if __name__ == "__main__":
    app.run(port=2025, debug=True)