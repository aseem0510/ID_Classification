# import necessary libraries
import datetime
import io
import os
import time
import urllib
import urllib.request

import cv2
import fitz
from memory_profiler import profile
import Models
import numpy as np
import requests
import uvicorn
from fastapi import FastAPI, Request, Response
from loguru import logger
from Models import MobileNet
import pandas as pd
from PIL import Image

app = FastAPI()

# importing models
model = Models.MobileNet.Mod_Mobile

# loading weights
model.load_weights("./Checkpoints/MobileNett1.h5")

# adding log file
logger.add(open("./Checkpoints/client.log", "w"))

@app.post("/idClassification/", status_code=200)
@profile
async def id_classification(response: Response, request: Request):
    """
    This method handles requests from user to perform ID Classification
    operation on different types of ID-Cards (Aadhar, Pan, Voter,
    Passport, Driving Lisence and Cheque)

    Parameters
    -----------
    url:str
            It represents url of an image

    :return: Json response consista information about particular
            classified IDs or errrors
    """

    start_time = time.time()

    logger.debug(f"Request hit time: {datetime.datetime.now()}")

    # waiting for data and converting it into json
    try:
        request = await request.json()

    except Exception:

        final_response = {
            "results": {
                "colorProfile": "unknown",
                "id_type": "unknown",
                "msg": "Invalid JSON Type",
                "status": "500",
            }
        }

        response.status_code = 500

        logger.warning("Invalid JSON Type")
        logger.info(
            "colorProfile: unknown, id_type: unknown, msg:\
 Invalid JSON Type, status: 500"
        )

        logger.debug(f"Response Time: {time.time()-start_time}")

        return final_response

    image = request["url"]

    # for handling number
    try:
        int(image)

        final_response = {
            "results": {
                "colorProfile": "unknown",
                "id_type": "unknown",
                "msg": "image url should contain image not number",
                "status": "422",
            }
        }

        response.status_code = 422

        logger.error("image url contains number")
        logger.info(
            "colorProfile: unknown, id_type: unknown, msg: image url\
 should contain image not number, status: 422"
        )

        logger.debug(f"Response Time: {time.time()-start_time}")

        return final_response

    except Exception:
        len(image)

    if len(image) == 0:

        final_response = {
            "results": {
                "colorProfile": "unknown",
                "id_type": "unknown",
                "msg": "image url is not allowed to be empty",
                "status": "422",
            }
        }

        response.status_code = 422

        logger.error("image url is empty")
        logger.info(
            "colorProfile: unknown, id_type: unknown, msg: image\
 url is not allowed to be empty, status: 422"
        )

        logger.debug(f"Response Time: {time.time()-start_time}")

        return final_response

    pdf = 1

    try:

        if ".gif" in image.lower():

            final_response = {
                "results": {
                    "colorProfile": "unknown",
                    "id_type": "unknown",
                    "msg": "url should be in jpg/jpeg/pdf/png format",
                    "status": "422",
                }
            }

            response.status_code = 422

            logger.error("given url is in gif format")
            logger.info(
                "colorProfile: unknown, id_type: unknown, msg:\
 url should be in jpg/jpeg/pdf/png format, status: 422"
            )

            logger.debug(f"Response Time: {time.time()-start_time}")

            return final_response

        elif ".pdf" in image.lower():
            pdf = 0

            # down_time = time.time()

            r = urllib.request.urlopen(image)

            # pdf_pre = time.time()

            filename = image.split("/")[-1]
            filename = "./images/" + str(filename[:-4])
            file = open(filename + ".pdf", "wb")

            file.write(r.read())
            file.close()

            pdf_file = fitz.open(filename + ".pdf")

            if len(pdf_file) >= 2:

                final_response = {
                    "results": {
                        "colorProfile": "unknown",
                        "id_type": "unknown",
                        "msg": "Given pdf url contains 2 or more pages",
                        "status": "422",
                    }
                }

                os.remove(filename + ".pdf")

                response.status_code = 422

                logger.error("pdf url contains 2 or more pages")
                logger.info(
                    "colorProfile: unknown, id_type: unknown, msg:\
 Given pdf url contains 2 or more pages, status: 422"
                )

                logger.debug(f"Response Time: {time.time()-start_time}")

                return final_response

            else:

                for page_index in range(len(pdf_file)):

                    # get the page itself
                    page = pdf_file[page_index]
                    page.get_images()

                    for image_index, img in enumerate(page.get_images(), start=1):

                        xref = img[0]

                        base_image = pdf_file.extract_image(xref)
                        image = base_image["image"]
                        image = np.fromstring(image, np.uint8)
                        image = cv2.imdecode(image, flags=1)

                os.remove(filename + ".pdf")

            # log.debug(f"Pdf operations:{time.time()-pdf_pre}")

        elif ".png" in image:

            image = Image.open(requests.get(image, stream=True).raw)

            num_channel = len(image.split())
            if num_channel == 4:
                image = image.convert("RGB")

        else:

            img = requests.get(image)
            image = Image.open(io.BytesIO(img.content))

        if pdf:
            num_channel = len(image.split())

            if num_channel == 4:
                image = image.convert("RGB")

        # converting image to n-d array
        temp_img = np.array(image)
        temp_img = cv2.resize(temp_img, (224, 224))
        temp_img = temp_img / 255.0
        temp_img = np.reshape(temp_img, [1, 224, 224, 3])

        # passing image to model
        # prediction = model.predict(temp_img)
        prediction = model(temp_img)
        prediction = prediction.numpy()

        result = prediction.argmax(axis=-1)

        ans = str(result[0])
        print(ans)

        if ans == "0":
            classes = "Aadhar Card"

        elif ans == "1":
            classes = "Pan Card"

        elif ans == "2":
            classes = "Voter ID"

        elif ans == "3":
            classes = "Driving Lisence"

        elif ans == "4":
            classes = "Passport"

        elif ans == "5":
            classes = "cheque"

        final_response = {
            "results": {
                "colorProfile": "COLOR",
                "id_type": str(classes),
                "msg": "success",
                "status": "200",
            }
        }

        response.status_code = 200

        logger.success("Successfully Classified")
        logger.info(
            "colorProfile: COLOR, id_type: {}, msg:\
 success, status: 200".format(
                str(classes)
            )
        )

        logger.debug(f"Response Time: {time.time()-start_time}")

        return final_response

    except Exception as e:
        print(e)
        final_response = {
            "results": {
                "colorProfile": "unknown",
                "id_type": "unknown",
                "msg": "Can you please check image url might expired",
                "status": "422",
            }
        }

        response.status_code = 422

        logger.error("Image url might expired")
        logger.info(
            "colorProfile: unknown, id_type: unknown, msg:\
 Can you please check image url might expired, status: 422"
        )

        logger.debug(f"Response Time: {time.time()-start_time}")

        return final_response


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")
