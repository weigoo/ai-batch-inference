from transformers import pipeline

classifier = None


def get_model():

    global classifier

    if classifier is None:
        print("Loading model...", flush=True)

        classifier = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english"
        )

        print("Model loaded", flush=True)

    return classifier


def run_inference(texts):

    model = get_model()

    return model(texts)