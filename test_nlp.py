from nlp_engine import nlp
import traceback

print("Testing NLP engine Location Stage for longer string...")

state = {"stage": "location", "law_key": "general"}
try:
    reply = nlp.generate_reply("I am in Chennai", "english", state)
    print("REPLY GENERATED SUCCESSFULLY")
except Exception as e:
    print("EXCEPTION CAUGHT IN TEST SCRIPT:")
    traceback.print_exc()
