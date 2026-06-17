import os
import pandas as pd
import pickle
import re
import random
from sentence_transformers import SentenceTransformer, util

# ---------------- TARGET LANGUAGES & DETECTION ---------------- #
TAMIL_UNICODE = r"[\u0B80-\u0BFF]"
HINDI_UNICODE = r"[\u0900-\u097F]"

def detect_language(text):
    text_l = text.lower()
    if re.search(TAMIL_UNICODE, text):
        return "tamil"
    if re.search(HINDI_UNICODE, text):
        return "hindi"
    if any(w in text_l for w in ["enna", "epdi", "kastam", "romba", "bayam", "panranga", "pesranga", "nadandhuchu", "sollunga", "adikkiranga", "valikidhu"]):
        return "tanglish"
    if any(w in text_l for w in ["kya", "kaise", "dar", "karna", "hai", "mujhe", "mera", "pati", "pareshan", "madad"]):
        return "hinglish"
    return "english"


# ---------------- INTERNAL INDIAN LAW EXPLANATION DATABASE ---------------- #
INDIAN_LAWS_DB = {
    "domestic_violence": {
        "english": "Under the Domestic Violence Act 2005, verbal, physical, or financial abuse in a shared household is strictly prohibited.",
        "tamil": "Domestic Violence Act 2005 இன் படி, குடும்பத்தில் நிகழும் உடல், மன, மற்றும் பொருளாதார துன்புறுத்தல்கள் சட்டப்படி குற்றமாகும்.",
        "hindi": "घरेलू हिंसा अधिनियम 2005 के तहत, घर में शारीरिक, मानसिक या आर्थिक शोषण पूरी तरह से गैरकानूनी है।",
        "tanglish": "Domestic Violence Act 2005 padithu paarkum podhu, veetla nadakkira physical, mental, illa financial abuse kandippa thappu.",
        "hinglish": "Domestic Violence Act 2005 ke tahat, ghar pe physical, mental ya financial abuse directly illegal hai."
    },
    "posh_act": {
        "english": "The POSH Act 2013 completely protects employees from sexual harassment at their workplace.",
        "tamil": "POSH Act 2013 சட்டம், வேலை செய்யும் இடத்தில் பெண்களுக்கு ஏற்படும் பாலியல் துன்புறுத்தல்களுக்கு எதிராக கடுமையான நடவடிக்கைகளை உறுதி செய்கிறது.",
        "hindi": "POSH एक्ट 2013 के अनुसार, कार्यस्थल पर महिलाओं के खिलाफ किसी भी तरह का यौन उत्पीड़न एक गंभीर अपराध है।",
        "tanglish": "POSH Act 2013 moolama, working place la nadakkira sexual harassment ku against ah neenga strict action edukallam.",
        "hinglish": "POSH Act 2013 ke according, workplace pe kisi bhi tarah ka sexual harassment ek serious crime hai."
    },
    "it_act_cyber": {
        "english": "The IT Act (Sections 66E, 67, 67A) heavily limits and punishes the spread of private information, identity theft, and online harassment.",
        "tamil": "IT Act (Sections 66E, 67) மூலமாக இணையத்தில் நடைபெறும் துன்புறுத்தல், தவறான புகைப்படங்கள் பகிர்தல் போன்ற செயல்களுக்கு சிறை தண்டனை வழங்க சட்டம் உள்ளது.",
        "hindi": "आईटी अधिनियम (IT Act Sections 66E, 67) के तहत ऑनलाइन उत्पीड़न या निजी जानकारी को इंटरनेट पर साझा करना कड़ा जुर्म है।",
        "tanglish": "IT Act (66E, 67) namba cyber spaces la, private info leak panradhu, illati online harassment panradha severe ah punish pannum.",
        "hinglish": "IT Act (66E, 67) cyber space me online harassment ya private info share karne walo ko jail proper punishment dilwata hai."
    },
    "ipc_assault_354": {
        "english": "Under IPC Section 354 and 354D, stalking, physical assault to outrage modesty, and unwanted contact are major crimes punishable by law.",
        "tamil": "IPC சட்டப்பிரிவு 354 மற்றும் 354D இன் படி, பின் தொடர்பவர்கள் (Stalking) அல்லது பாலியல் சீண்டல் செய்வோருக்கு எதிராக குற்ற வழக்கு பதிவு செய்யலாம்.",
        "hindi": "IPC की धारा 354 और 354D के तहत छेड़छाड़ करना, पीछा करना या डराना बहुत संगीन अपराध माने जाते हैं।",
        "tanglish": "IPC Section 354 madrum 354D moolama yaarachu unnai stalk pannale, illa unwanted contact vechikitta, FIR podalam.",
        "hinglish": "IPC 354 aur 354D ke tehat agar koi physical harm kare ya stalk kare, toh ye straight cognizable crime hota hai."
    },
    "ipc_criminal_intimidation_506": {
        "english": "IPC Section 504 and 506 protects individuals against criminal intimidation or death threats.",
        "tamil": "IPC பிரிவு 504 மற்றும் 506 இன் கீழ், உங்களை பயமுறுத்துவது அல்லது கொலை மிரட்டல் விடுப்பது சட்ட விரோத செயலாகும்.",
        "hindi": "आईपीसी की धारा 504 और 506 के तहत किसी को भी डराना या जान से मारने की धमकी देना एक अपराध है।",
        "tanglish": "IPC 504 and 506 padi, unnai veruthan mirattina illa hurt panren nu sonna dhairiyam ah action edukalam.",
        "hinglish": "IPC 504 and 506 ke according koi aapko physical harm ka threat de toh police unko arrest kar sakti hai."
    },
    "general": {
         "english": "The Indian Constitution and Penal codes provide rigorous systemic protections protecting your basic human rights.",
         "tamil": "இந்திய அரசியலமைப்பு மற்றும் சட்டங்கள் உங்களின் அடிப்படை மனித உரிமைகளை எப்போதும் பாதுகாக்கும்.",
         "hindi": "भारतीय संविधान और दंड संहिता आपके बुनियादी मानवाधिकारों की रक्षा के लिए सख्त सुरक्षा प्रदान करते हैं।",
         "tanglish": "Indian Constitution unga basic human rights ah protect pandradhuku neraiya strict laws vachi irukku.",
         "hinglish": "Indian Constitution aur laws aapke fundamental rights ko har haal mein protect karne ke liye bane hain."
    }
}

# ---------------- EMPATHETIC ASSEMBLY BLOCKS ---------------- #
# We randomly choose across these elements to form incredibly dynamic ChatGPT-like arrays offline.
CONVERSATIONAL_BLOCKS = {
    "english": {
        "empathy_legal": ["I'm so sorry you're going through this. Please know you are not alone. 🤝", "It takes immense courage to share this. This situation is unacceptable, and the law protects you here. 🛡️"],
        "empathy_pure": ["I hear you, and I am so sorry you feel this way right now. 💙", "It's completely okay to feel overwhelmed. I am here for you. 🤗"],
        "actions": [
            "<ul><li>🚨 <b>Document Everything:</b> Save messages, photos, and any evidence.</li><li>🏃 <b>Find Safety:</b> Try to distance yourself from the person harming you.</li><li>📞 <b>Get Help:</b> Call the National Commission for Women (1091) or Police (100).</li></ul>",
            "<ul><li>🗣️ <b>Reach out:</b> Connect with a trusted family member or friend.</li><li>💾 <b>Preserve Evidence:</b> Never delete chats or logs related to the abuse.</li><li>🚓 <b>Action:</b> Visit the nearest police station or dial 100 immediately if you feel threatened.</li></ul>"
        ],
        "share_more": "Do you want to share more about what is causing you stress? 🗣️",
        "follow_up_question": "I am so sorry to hear this. Could you please tell me a bit more about how severe the situation is so I can understand if it requires formal legal action?",
        "lawyer_title": "Recommended Legal Counsel Nearby:",
        "lawyer_footer": "Please reach out to them for immediate legal representation. ⚖️",
        "no_lawyer_found": "We couldn't heavily align a lawyer in your specific city right now, but please contact the local authorities for immediate help.",
        "ask_location": "Please tell me your city or location so I can share the contact details of our most recommended lawyers near you. 🏥"
    },
    "tamil": {
        "empathy_legal": ["இந்த கடினமான சூழ்நிலையை நீங்கள் தனியாக கடக்க வேண்டியதில்லை. நான் உங்களுடன் இருக்கிறேன். 🤝", "இதை பற்றி பேச நீங்கள் எடுத்த தைரியம் சிறந்தது. சட்டம் உங்களுக்கு துணையாக இருக்கும். 🛡️"],
        "empathy_pure": ["உங்களுக்கு ஆறுதலாக நான் இங்கு இருக்கிறேன், உங்கள் கவலை எனக்குப் புரிகிறது. 💙", "கஷ்டமாகத் தோன்றுவது இயல்பு தான். உங்களை நீங்களே பாதுகாத்துக்கொள்ளுங்கள். 🤗"],
        "actions": [
            "<ul><li>🚨 <b>ஆதாரங்களை சேகரியுங்கள்:</b> குறுஞ்செய்திகள் மற்றும் புகைப்படங்களை பத்திரமாக வைக்கவும்.</li><li>📞 <b>உதவி நாடுங்கள்:</b> பெண்கள் உதவி மையம் (1091) அல்லது காவல்துறையை (100) தொடர்பு கொள்ளுங்கள்.</li></ul>"
        ],
        "share_more": "உங்களுக்கு மன அழுத்தத்தை ஏற்படுத்துவது குறித்து மேலும் பகிர விரும்புகிறீர்களா? 🗣️",
        "follow_up_question": "இதை கேட்க மிகவும் வருத்தமாக இருக்கிறது. உங்களுக்கு சட்டப்படியான உதவி தேவையா என்பதை புரிந்துகொள்ள, இது எந்த அளவு தீவிரமான பிரச்சனை என சற்று விளக்க முடியுமா?",
        "lawyer_title": "உங்களுக்கு அருகிலுள்ள சிறந்த வழக்கறிஞர்:",
        "lawyer_footer": "உடனடி சட்ட உதவி பெற இவரைத் தொடர்பு கொள்ளவும். ⚖️",
        "no_lawyer_found": "தற்போது உங்கள் பகுதியில் எங்களால் பிரத்தியேக வழக்கறிஞரைப் பரிந்துரைக்க முடியவில்லை. தயவுசெய்து காவல்துறை உதவியை நாடவும்.",
        "ask_location": "தயவுசெய்து உங்கள் ஊர் அல்லது நகரத்தை தெரிவிக்கவும். உங்கள் அருகிலுள்ள சிறந்த வழக்கறிஞரின் தொடர்பு எண்ணை நான் பகிர்கிறேன். 🏥"
    },
    "hindi": {
        "empathy_legal": ["मुझे बहुत दुख है कि आपको इसका सामना करना पड़ रहा है। कानून आपके पक्ष में है। 🤝", "यह स्थिति बहुत दर्दनाक हो सकती है, लेकिन याद रखें कि आप अकेले नहीं हैं। 🛡️"],
        "empathy_pure": ["मैं समझ सकता हूँ कि आप कितना अकेला महसूस कर रहे हैं, लेकिन मैं आपके साथ हूँ। 💙", "रोने या परेशान होने में कोई बुराई नहीं है। स्थिति बेहतर हो सकती है। 🤗"],
        "actions": [
            "<ul><li>🚨 <b>सबूत सुरक्षित रखें:</b> सभी मैसेज और कॉल लॉग सेव करें।</li><li>🏃 <b>सुरक्षित रहें:</b> उस इंसान से दूर हो जाएं।</li><li>📞 <b>तुरंत मदद लें:</b> 1091 (महिला हेल्पलाइन) या 100 (पुलिस) डायल करें।</li></ul>"
        ],
        "share_more": "क्या आप साझा करना चाहते हैं कि आपको क्या परेशानी हो रही है? 🗣️",
        "follow_up_question": "यह सुनकर मुझे बहुत खेद है। क्या आप मुझे बता सकते हैं कि यह स्थिति कितनी गंभीर है, ताकि मैं समझ सकूं कि क्या इसमें कानूनी मदद की आवश्यकता है?",
        "lawyer_title": "अनुशंसित कानूनी सलाहकार:",
        "lawyer_footer": "तत्काल कानूनी सहायता के लिए कृपया इनसे संपर्क करें। ⚖️",
        "no_lawyer_found": "वर्तमान में हम आपके शहर में किसी वकील की सिफारिश नहीं कर पा रहे हैं। कृपया तुरंत 100 डायल करके पुलिस से संपर्क करें।",
        "ask_location": "कृपया मुझे अपना शहर या स्थान बताएं ताकि मैं आपके आस-पास के सबसे अच्छे वकीलों के विवरण साझा कर सकूं। 🏥"
    },
    "tanglish": {
        "empathy_legal": ["Idhu romba kastam nu enaku puriyudhu. Neenga thaniya illa, law kandippa support pannum. 🤝", "Ippadi nadakka koodathu. Itha pethi pesa neenga romba dhairiyam eduthurukinga. 🛡️"],
        "empathy_pure": ["Neenga romba feel pandringa nu puriyudhu. Naan ungalukku help panna iruken. 💙", "Kavalaipadatheenga. Ellam konjam konjam ah sari aagirum. 🤗"],
        "actions": [
            "<ul><li>🚨 <b>Save Everything:</b> Ella chats, calls um record panni vechikonga.</li><li>🏃 <b>Safe ah Irunga:</b> Antha alu kitta irundhu thalli irunga.</li><li>📞 <b>Get Help:</b> 1091 illa 100 call panni udane police help kelunga.</li></ul>"
        ],
        "share_more": "Unga problem pethi innum detail ah share panna virumburingala? 🗣️",
        "follow_up_question": "Idha kekave kastama iruku. Idhu evlo serious aana problem nu konjam detail ah solla mudiyuma? Appadhan legal action thevaya nu puriyum.",
        "lawyer_title": "Ungaluku pakkathula iruka best lawyer details:",
        "lawyer_footer": "Immediate legal help ku ivangala contact pannunga. ⚖️",
        "no_lawyer_found": "Ippa unga area la lawyer kedaikala, but immediate ah police help thedunga.",
        "ask_location": "Dhayavusenju unga city illa area location sollunga, na pakkathula iruka nalla lawyer details tharen. 🏥"
    },
    "hinglish": {
        "empathy_legal": ["Mujhe afsos hai ki aapko yeh face karna pad raha hai. Law puri tarah aapke side hai. 🤝", "Yeh kaafi difficult time hoga, but aap akele nahi hain. System aapko protect karega. 🛡️"],
        "empathy_pure": ["Main understand kar sakta hoon ki aap kaisa feel kar rahe hain. 💙", "Aap tension mat lijiye. Main yahan aapki baat sunne ke liye hoon. 🤗"],
        "actions": [
            "<ul><li>🚨 <b>Document Karein:</b> Jo bhi messages ya abuse hai, sab save karein.</li><li>🏃 <b>Safety First:</b> Uss insaan se dur rahein.</li><li>📞 <b>Action Lein:</b> Turant 100 ya 1091 par call karein.</li></ul>"
        ],
        "share_more": "Kya aap share karna chahenge ki aapko stress kyu lag raha hai? 🗣️",
        "follow_up_question": "Yeh sunkar mujhe bahut dukh hua. Kya aap situation ki severity thoda aur bata sakte hain, taaki main samajh saku ki legal action ki zarurat hai ya nahi?",
        "lawyer_title": "Aapke nazdik best lawyer details:",
        "lawyer_footer": "Turant legal step lene ke liye inko contact karein. ⚖️",
        "no_lawyer_found": "Abhi aapke area me specific lawyer ki details available nahi hai, but quickly local police se help lijiye.",
        "ask_location": "Please apni city ya location bataiye taaki main nearest lawyer details share kar saku. 🏥"
    }
}


# ---------------- HYBRID NLU ENGINE ---------------- #
class HighFidelityHybridEngine:
    def __init__(self, dataset_path="indian_legal_abuse_dataset_50000.csv", lawyers_dataset_path="Lawyers.xlsx"):
        self.dataset_path = dataset_path
        self.lawyers_dataset_path = lawyers_dataset_path
        self.embeddings_cache = "ai/dataset_embeddings.pkl"
        
        print("Initializing High-Fidelity NLU Assembler...")
        self.retrieval_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        self.df = None
        self.corpus_embeddings = None
        self.df_lawyers = None
        self.locations = []
        
        # Load custom AI models
        self.severity_pipeline = None
        if os.path.exists("ai/severity_model.pkl"):
            with open("ai/severity_model.pkl", "rb") as f:
                self.severity_pipeline = pickle.load(f)
                
        self.lawyer_recommender = None
        if os.path.exists("ai/lawyer_recommender.pkl"):
            with open("ai/lawyer_recommender.pkl", "rb") as f:
                self.lawyer_recommender = pickle.load(f)
        
        if os.path.exists(self.dataset_path):
            self.load_dataset()
        else:
            print(f"Warning: Dataset {self.dataset_path} not found.")

    def load_dataset(self):
        # Load main text dataset
        df = pd.read_csv(self.dataset_path).dropna(subset=['text', 'law', 'abuse_type'])
        self.df = df.drop_duplicates(subset=['text']).reset_index(drop=True)
        
        if not os.path.exists("ai"):
            os.makedirs("ai")
            
        if os.path.exists(self.embeddings_cache):
            with open(self.embeddings_cache, "rb") as f:
                self.corpus_embeddings = pickle.load(f)
        else:
            self.corpus_embeddings = self.retrieval_model.encode(self.df['text'].tolist(), convert_to_tensor=True, show_progress_bar=False)
            with open(self.embeddings_cache, "wb") as f:
                pickle.dump(self.corpus_embeddings, f)
            print("Embeddings loaded into NLU.")
            
        # Load lawyers dataset
        if os.path.exists(self.lawyers_dataset_path):
            try:
                self.df_lawyers = pd.read_excel(self.lawyers_dataset_path)
                if 'Location' in self.df_lawyers.columns:
                    self.locations = [str(x).lower() for x in self.df_lawyers['Location'].unique()]
                print("Lawyers dataset loaded into NLU.")
            except Exception as e:
                print(f"Failed to load lawyers dataset: {e}")
            
    def map_detailed_law(self, extracted_law):
        law = str(extracted_law).lower()
        if "domestic" in law or "498a" in law:
            return "domestic_violence"
        elif "posh" in law:
            return "posh_act"
        elif "it act" in law or "66e" in law or "67" in law:
            return "it_act_cyber"
        elif "354" in law:
            return "ipc_assault_354"
        elif "506" in law or "504" in law:
            return "ipc_criminal_intimidation_506"
        return "general"

    def match_intent(self, user_text):
        if self.corpus_embeddings is None:
            return None
            
        query_embedding = self.retrieval_model.encode(user_text, convert_to_tensor=True)
        hits = util.semantic_search(query_embedding, self.corpus_embeddings, top_k=1)[0]
        
        best_hit = hits[0]
        
        # NLU Decision Thresholding:
        # High Score -> Definite Legal Incident
        # Low Score -> Just emotional distress / casual
        
        if best_hit['score'] > 0.45:
            row = self.df.iloc[best_hit['corpus_id']]
            mapped_key = self.map_detailed_law(row['law'])
            return {
                "type": "legal",
                "law_key": mapped_key,
                "raw_law": row['law']
            }
        else:
            return {
                "type": "emotional"
            }

    def detect_location(self, text):
        if not self.locations:
            return None
        text_lower = text.lower()
        for loc in self.locations:
            if loc in text_lower:
                return loc.title()
        return None

    def generate_reply(self, user_msg, lang, state):
        stage = state.get("stage", "start")
        blocks = CONVERSATIONAL_BLOCKS.get(lang, CONVERSATIONAL_BLOCKS["english"])
        
        # Short Greetings Handshake
        if stage == "start" or len(user_msg.split()) <= 2:
            state["stage"] = "investigating"
            if lang == "tamil": return "வணக்கம்! 🙏 நான் UCASE. இன்று உங்களுக்கு என்ன சட்ட மற்றும் உணர்வு ரீதியான உதவி தேவை? 🤖"
            if lang == "hindi": return "नमस्ते! 🙏 मैं UCASE हूँ। आज मैं आपकी क्या मदद कर सकता हूँ? 🤖"
            if lang == "tanglish": return "Vanakkam! 🙏 UCASE inaiku ungalukku eppadi help panna mudiyum? 🤖"
            if lang == "hinglish": return "Namaste! 🙏 UCASE se main aapki aaj kya help kar sakta hu? 🤖"
            return "Hello! 👋 I am UCASE, your legal assistant. How can I help you today? 🤖"

        # Stage 1: Investigating intent of the user statement
        if stage == "investigating" or stage == "responding":
            intent_data = self.match_intent(user_msg)
            
            if intent_data["type"] == "emotional":
                # Pure Emotional Support Mode
                empathy = random.choice(blocks["empathy_pure"])
                return f"{empathy}<br><br><b>{blocks['share_more']}</b>"
            else:
                # Potential Legal Need found. Do NOT give lawyer yet. Ask a follow-up.
                state["stage"] = "followup"
                state["law_key"] = intent_data["law_key"]
                
                empathy = random.choice(blocks["empathy_legal"])
                return f"{empathy}<br><br><b>{blocks['follow_up_question']}</b>"

        # Stage 2: Followup to assess Severity using AI Model
        if stage == "followup":
            is_severe = 0
            if self.severity_pipeline:
                try:
                    probs = self.severity_pipeline.predict_proba([user_msg])[0]
                    # if probability of Severe/LegalAction class > 0.4
                    if probs[1] > 0.4:
                        is_severe = 1
                except Exception as e:
                    pass
            else:
                # Fallback primitive check if model missing
                if any(w in user_msg.lower() for w in ["yes", "lawyer", "police", "action", "severe", "help", "haan", "aama"]):
                    is_severe = 1

            law_key = state.get("law_key", "general")
            law_db = INDIAN_LAWS_DB.get(law_key, INDIAN_LAWS_DB["general"])
            law_explanation = law_db.get(lang, law_db["english"])
            
            if is_severe == 1:
                state["stage"] = "location"
                return f"<b>{law_explanation}</b><br><br>📍 <b>{blocks['ask_location']}</b>"
            else:
                # low severity -> give actions and end securely
                actions = random.choice(blocks["actions"])
                state["stage"] = "investigating" # reset to investigate for next queries
                return f"<b>{law_explanation}</b><br><br>{actions}<br><br><i>Please remember, you can always ask for a lawyer if things escalate.</i>"

        # Stage 3: Process Location and suggest Lawyer using ML Recommender
        if stage == "location":
            detected_loc = self.detect_location(user_msg)
            # if explicit location not found, use their word as location fallback
            query_loc = detected_loc if detected_loc else user_msg.strip()
            
            law_key = state.get("law_key", "general")
            
            # Use Trained Lawyer Recommender ML Model
            if self.lawyer_recommender:
                # Map system law intent to generic practice area spaces
                pr_map = {
                    "domestic_violence": "Criminal",
                    "posh_act": "Corporate",
                    "it_act_cyber": "Civil",
                    "ipc_assault_354": "Criminal",
                    "ipc_criminal_intimidation_506": "Criminal",
                    "general": "Civil"
                }
                target_practice = pr_map.get(law_key, "Civil")
                query_text = f"{query_loc} {target_practice}"
                
                try:
                    vec = self.lawyer_recommender["vectorizer"].transform([query_text])
                    distances, indices = self.lawyer_recommender["knn_model"].kneighbors(vec)
                    
                    best_idx = indices[0][0]
                    df_lawyers = self.lawyer_recommender["dataframe"]
                    best_lawyer = df_lawyers.iloc[best_idx]
                    
                    lawyer_info = (f"🧑‍⚖️ <b>{blocks['lawyer_title']}</b><br>"
                                   f"🏷️ <b>Name:</b> {best_lawyer['Name']}<br>"
                                   f"📞 <b>Contact:</b> {best_lawyer['Mobile Number']}<br>"
                                   f"📍 <b>Location:</b> {best_lawyer['Location']}<br>"
                                   f"⚖️ <b>Practice/Expertise:</b> {best_lawyer['Practice Area']} ({best_lawyer['Experience (Years)']} yrs)<br>"
                                   f"<br><i>{blocks['lawyer_footer']}</i>")
                    state["stage"] = "investigating" # Reset to handle generic conversations next
                    return lawyer_info
                except Exception as e:
                    pass
            
            # Normal fallback filtering if Recommender missing
            if self.df_lawyers is not None and detected_loc:
                filtered = self.df_lawyers[self.df_lawyers['Location'].str.lower() == detected_loc.lower()]
                if not filtered.empty:
                    best_lawyer = filtered.sort_values(by='Experience (Years)', ascending=False).iloc[0]
                    lawyer_info = (f"🧑‍⚖️ <b>{blocks['lawyer_title']}</b><br>"
                                   f"🏷️ <b>Name:</b> {best_lawyer['Name']}<br>"
                                   f"📞 <b>Contact:</b> {best_lawyer['Mobile Number']}<br>"
                                   f"📍 <b>Location:</b> {best_lawyer['Location']}<br>"
                                   f"⚖️ <b>Practice/Expertise:</b> {best_lawyer['Practice Area']} ({best_lawyer['Experience (Years)']} yrs)<br>"
                                   f"<br><i>{blocks['lawyer_footer']}</i>")
                    state["stage"] = "investigating"
                    return lawyer_info

            state["stage"] = "investigating"
            return f"⚠️ <i>{blocks['no_lawyer_found']}</i>"

# Initialize Global Instance
nlp = HighFidelityHybridEngine()
