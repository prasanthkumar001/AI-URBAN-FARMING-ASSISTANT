"""
Voice AI Assistant Service for KrishiNova.
Provides multi-lingual AI doubt clarification for urban gardeners and farmers
in Gujarati (ગુજરાતી), Hindi (हिन्दी), Telugu (తెలుగు), and English.
Includes Speech Recognition & Speech Synthesis (TTS) configuration and
domain-specific agricultural intelligence.
"""

import re
from datetime import datetime

# Supported Languages & Web Speech API Locales
SUPPORTED_LANGUAGES = {
    "en": {
        "code": "en",
        "name": "English",
        "native": "English",
        "flag": "🇬🇧",
        "speech_locale": "en-IN",
        "voice_gender": "female",
        "mic_prompt": "Tap the microphone and speak your gardening question...",
        "listening_label": "Listening... Speak now",
        "ask_btn": "Ask KrishiNova AI",
        "speak_btn": "Listen (Voice)",
        "stop_speech_btn": "Stop Audio",
        "sample_questions": [
            "Why are my tomato leaves turning yellow with brown spots?",
            "How often should I water balcony plants in summer?",
            "How to prepare organic neem oil spray for whiteflies?",
            "Which organic fertilizer is best for flowering chillies?",
            "How to prevent blossom end rot in container tomatoes?"
        ]
    },
    "gu": {
        "code": "gu",
        "name": "Gujarati",
        "native": "ગુજરાતી",
        "flag": "🇮🇳",
        "speech_locale": "gu-IN",
        "voice_gender": "female",
        "mic_prompt": "માઇક્રોફોન દબાવો અને તમારી ખેતી કે બગીચાની સમસ્યા બોલો...",
        "listening_label": "સાંભળી રહ્યા છીએ... હવે બોલો",
        "ask_btn": "કૃષિનોવા AI ને પૂછો",
        "speak_btn": "અવાજ સાંભળો (Voice)",
        "stop_speech_btn": "અવાજ બંધ કરો",
        "sample_questions": [
            "ટામેટાના પાંદડા પીળા પડી જાય છે અને સુકાઈ રહ્યા છે, શું કરવું?",
            "ગરમીમાં કૂંડાના છોડને ક્યારે અને કેટલું પાણી આપવું?",
            "મરચીના છોડમાં મરોડિયા રોગ અને સફેદ માખી માટે દેશી ઉપાય?",
            "કૂંડામાં શાકભાજી માટે કયું દેશી ખાતર શ્રેષ્ઠ છે?",
            "લીમડાના તેલનો સ્પ્રે કેવી રીતે બનાવવો?"
        ]
    },
    "hi": {
        "code": "hi",
        "name": "Hindi",
        "native": "हिन्दी",
        "flag": "🇮🇳",
        "speech_locale": "hi-IN",
        "voice_gender": "female",
        "mic_prompt": "माइक दबाएं और अपनी खेती या बागवानी का सवाल बोलें...",
        "listening_label": "सुन रहे हैं... कृपया बोलिए",
        "ask_btn": "कृषिनोवा AI से पूछें",
        "speak_btn": "आवाज सुनें (Voice)",
        "stop_speech_btn": "आवाज रोकें",
        "sample_questions": [
            "टमाटर के पत्तों पर काले-भूरे धब्बे आ रहे हैं, क्या इलाज करें?",
            "गर्मी में बालकनी के गमलों में पानी कब और कैसे देना चाहिए?",
            "मिर्च के पौधों में पत्ती मरोड़ और कीड़ों से बचाव के उपाय?",
            "घर के गमलों के लिए नीम के तेल का स्प्रे कैसे बनाएं?",
            "फूल और फल झड़ने से रोकने के लिए कौन सी जैविक खाद डालें?"
        ]
    },
    "te": {
        "code": "te",
        "name": "Telugu",
        "native": "తెలుగు",
        "flag": "🇮🇳",
        "speech_locale": "te-IN",
        "voice_gender": "female",
        "mic_prompt": "మైక్రోఫోన్ నొక్కి మీ వ్యవసాయం లేదా తోట సందేహాన్ని మాట్లాడండి...",
        "listening_label": "వింటున్నాము... ఇప్పుడు మాట్లాడండి",
        "ask_btn": "కృషినోవా AI ని అడగండి",
        "speak_btn": "వినండి (Voice)",
        "stop_speech_btn": "వాయిస్ ఆపండి",
        "sample_questions": [
            "టమోటా ఆకులు పసుపు రంగులోకి మారి మచ్చలు వస్తున్నాయి, ఏమి చేయాలి?",
            "వేసవిలో బాల్కనీ కుండీలలో మొక్కలకు ఎప్పుడు నీరు పోయాలి?",
            "మిరప మొక్కల్లో ముడత తెగులు నివారణకు సహజ మందు ఏమిటి?",
            "కుండీలలో కూరగాయలకు ఏ సేంద్రియ ఎరువు మంచిది?",
            "వేప నూనె స్ప్రేని ఇంట్లోనే ఎలా తయారు చేసుకోవాలి?"
        ]
    }
}

# Domain Agricultural Knowledge Base for Clarifying Doubts
KNOWLEDGE_TOPICS = {
    "yellow_leaves": {
        "keywords": ["yellow", "पीला", "पीले", "પીળા", "પીળું", "పసుపు", "spots", "blight", "chlorosis", "धब्बे", "કાળા", "మచ్చలు"],
        "en": {
            "topic": "Leaf Yellowing & Fungal Spots",
            "summary": "Yellowing leaves with spots usually indicate Early Blight or overwatering in balcony containers.",
            "steps": [
                "1. Soil Moisture Check: Ensure the pot has drainage holes and upper 2 inches of soil are dry before watering.",
                "2. Sanitation: Trim and discard infected lower yellow leaves with clean shears. Do not compost them.",
                "3. Air Circulation: Space pots 1 foot apart on the balcony for breeze flow.",
                "4. Organic Treatment: Spray organic neem oil solution (5ml neem oil + 2ml liquid soap in 1L water) early morning."
            ],
            "speech": "Yellowing leaves are usually caused by fungal leaf spot or overwatering. Trim infected lower leaves and spray organic neem oil early morning. Make sure the container soil drains properly.",
            "tips": "Never water plant foliage directly from overhead; water at the root base."
        },
        "gu": {
            "topic": "પાંદડા પીળા પડવા અને ડાઘા (સુકારો)",
            "summary": "પાંદડા પીળા પડી ડાઘા પડવા એ વધુ પડતા પાણી અથવા ફંગલ ઇન્ફેક્શન (સુકારો/અલ્ટરનેરિયા) નું લક્ષણ છે.",
            "steps": [
                "૧. પાણી તપાસો: કૂંડાના તળિયે કાણું હોવું જરૂરી છે. માટી ઉપરથી ૨ ઇંચ સૂકી થાય ત્યારે જ પાણી આપો.",
                "૨. પીળા પાન દૂર કરો: નીચેના ચેપગ્રસ્ત પાંદડા કાપીને કચરામાં નાખી દો.",
                "૩. હવા-ઉજાસ: કૂંડાઓને પૂરતો સૂર્યપ્રકાશ અને હવા મળે તેવી જગ્યાએ રાખો.",
                "૪. દેશી ઉપચાર: ૧ લિટર પાણીમાં ૫ મિ.લી. લીમડાનું તેલ અને ૨ ટીપાં લિક્વિડ સાબુ મેળવી સવારે છંટકાવ કરો."
            ],
            "speech": "પાંદડા પીળા પડવાનું કારણ ફંગસ અથવા કૂંડામાં વધુ પાણી હોઈ શકે છે. નીચેના પીળા પાન કાપી લો અને સવારે લીમડાના તેલનો છંટકાવ કરો. કૂંડામાં પાણી ભરાઈ ન રહે તેનું ધ્યાન રાખો.",
            "tips": "છોડના પાંદડા પર ઉપરથી પાણી રેડવાને બદલે હંમેશા મૂળના ભાગે પાણી આપો."
        },
        "hi": {
            "topic": "पत्तियों का पीला पड़ना और धब्बे (ब्लाइट)",
            "summary": "पत्तियों का पीला होना और धब्बे पड़ना फंगल संक्रमण (अगेती झुलसा) या गमले में ज्यादा पानी जमा होने का संकेत है।",
            "steps": [
                "1. पानी की जांच: गमले के नीचे जल निकासी छेद खुला रखें। ऊपर की 2 इंच मिट्टी सूखने पर ही पानी दें।",
                "2. छंटाई: नीचे की पीली व दागदार पत्तियों को साफ कैंची से काटकर अलग फेंक दें।",
                "3. हवा और धूप: बालकनी में पौधों को पर्याप्त धूप और खुली हवा में रखें।",
                "4. जैविक उपचार: 1 लीटर पानी में 5ml नीम का तेल और 2 बूंद साबुन घोलकर सुबह के समय छिड़काव करें।"
            ],
            "speech": "पत्तियों का पीला पड़ना फफूंद या अधिक पानी के कारण होता है। नीचे की खराब पत्तियां काट दें और सुबह नीम के तेल का छिड़काव करें। गमले में जल निकासी का ध्यान रखें।",
            "tips": "पत्तियों पर ऊपर से पानी डालने से बचें; हमेशा पौधे की जड़ों के पास पानी डालें।"
        },
        "te": {
            "topic": "ఆకులు పసుపు రంగులోకి మారడం & మచ్చల తెగులు",
            "summary": "ఆకులు పసుపుగా మారి మచ్చలు రావడం అధిక నీరు లేదా ఫంగస్ (ఆకుమచ్చ తెగులు) వల్ల వస్తుంది.",
            "steps": [
                "1. నీటి తేమ తనిఖీ: కుండీ అడుగున రంధ్రం సరిగ్గా ఉందో లేదో చూడండి. పై మట్టి ఆరిన తర్వాతే నీరు పోయాలి.",
                "2. కత్తిరింపు: తెగులు సోకిన కిందటి పసుపు ఆకులను కత్తిరించి తీసివేయండి.",
                "3. గాలి మరియు ఎండ: మొక్కలకు 6 గంటల ఎండ మరియు మంచి గాలి తగిలేలా ఉంచండి.",
                "4. సహజ నివారణ: 1 లీటర్ నీటిలో 5 మిల్లీలీటర్ల వేపనూనె, కొద్దిగా సబ్బు నీరు కలిపి ఉదయం వేళ పిచికారీ చేయండి."
            ],
            "speech": "ఆకులు పసుపుగా మారడం ఫంగస్ లేదా ఎక్కువ నీరు పోయడం వల్ల జరుగుతుంది. పాడైన ఆకులను తీసేసి ఉదయాన్నే వేప నూనె ద్రావణాన్ని పిచికారీ చేయండి.",
            "tips": "ఆకులపై నీరు చల్లకుండా ఎల్లప్పుడూ మొదట్లో మాత్రమే నీరు పోయండి."
        }
    },
    "watering": {
        "keywords": ["water", "watering", "dry", "पानी", "जल", "પાણી", "સિંચાઈ", "నీరు", "తడి", "ఎండ", "summer", "heat", "ગરમી", "गर्मी", "వేసవి"],
        "en": {
            "topic": "Smart Container Watering Schedule",
            "summary": "Urban pots dry out rapidly in balcony breezes and afternoon heat.",
            "steps": [
                "1. Morning Timing: Water early between 6 AM and 8 AM to prevent midday heat evaporation.",
                "2. Finger Test: Insert your finger 1 inch into soil; if moist, skip watering today.",
                "3. Terracotta Pots: Unglazed clay pots lose moisture 30% faster than plastic containers.",
                "4. Mulch Layer: Spread dried leaves or cocopeat on the topsoil to lock in moisture."
            ],
            "speech": "Water your balcony plants early in the morning before the sun gets strong. Use the finger test to check if the topsoil is dry before pouring water.",
            "tips": "Always check weather alerts in KrishiNova: if rain is forecast, hold off watering."
        },
        "gu": {
            "topic": "કૂંડામાં સ્માર્ટ પાણી આપવાની રીત",
            "summary": "બાલકની અને ટેરેસ પર પવન અને તડકાને કારણે કૂંડાની માટી ઝડપથી સુકાઈ જાય છે.",
            "steps": [
                "૧. સવારનો સમય: સવારે ૬ થી ૮ વાગ્યા વચ્ચે પાણી આપો જેથી બપોરના તડકામાં બાષ્પીભવન ન થાય.",
                "૨. આંગળીથી માટી ચકાસો: માટીમાં ૧ ઇંચ આંગળી નાખી તપાસો; જો ભેજ હોય તો આજે પાણી ન આપો.",
                "૩. માટીના કૂંડા: માટીના કૂંડા પ્લાસ્ટિક કરતા ઝડપથી સુકાય છે, તેમાં વધુ ધ્યાન આપો.",
                "૪. મલ્ચિંગ: કૂંડાની સપાટી પર સૂકા પાંદડા અથવા કોકોપીટ પાથરો જેથી ભેજ જળવાઈ રહે."
            ],
            "speech": "બાલકનીના છોડને વહેલી સવારે પાણી આપો. કૂંડાની માટીમાં આંગળી નાખી ભેજ તપાસ્યા પછી જ પાણી રેડો જેથી મૂળ સડી ન જાય.",
            "tips": "કૃષિનોવા એપમાં વરસાદની આગાહી જોઈને પાણી આપો; વરસાદ હોય તો પાણી ટાળો."
        },
        "hi": {
            "topic": "गमलों में सही सिंचाई एवं पानी का नियम",
            "summary": "बालकनी और छत के गमलों में धूप और हवा के कारण नमी बहुत जल्दी उड़ जाती है।",
            "steps": [
                "1. सुबह का समय: सुबह 6 से 8 बजे के बीच पानी दें ताकि दोपहर की धूप में मिट्टी न सूखे।",
                "2. उंगली से जांच: मिट्टी में 1 इंच उंगली डालकर देखें; यदि मिट्टी में नमी है तो आज पानी न दें।",
                "3. गमले का प्रकार: मिट्टी के गमलों में प्लास्टिक गमलों की तुलना में जल्दी नमी खत्म होती है।",
                "4. मल्चिंग: गमले की ऊपरी सतह पर सूखे पत्ते या कोकोपीट बिछाएं ताकि नमी बनी रहे।"
            ],
            "speech": "गमले के पौधों को सुबह जल्दी पानी दें। पानी देने से पहले मिट्टी में उंगली डालकर नमी जरूर जांचें ताकि जड़ें सड़ने से बच सकें।",
            "tips": "कृषिनोवा में मौसम का पूर्वानुमान देखें; यदि बारिश होने वाली है तो पानी न दें।"
        },
        "te": {
            "topic": "కుండీలలో మొక్కలకు నీటి యాజమాన్యం",
            "summary": "బాల్కనీలలో ఎండ మరియు గాలి వలన కుండీలలోని మట్టి త్వరగా ఎండిపోతుంది.",
            "steps": [
                "1. ఉదయం సమయం: ఉదయం 6 నుండి 8 గంటల మధ్యలో నీరు పోయండి, మధ్యాహ్నం ఎండలో పోయవద్దు.",
                "2. తేమ పరీక్ష: మట్టిలో ఒక అంగుళం వేలు పెట్టి చూడండి; తేమ ఉంటే ఈ రోజు నీరు పోయవద్దు.",
                "3. కుండీ రకం: మట్టి కుండీలలో ప్లాస్టిక్ కుండీల కంటే నీరు త్వరగా ఆరిపోతుంది.",
                "4. ఆచ్ఛాదన (మల్చింగ్): మట్టి తేమ ఆరిపోకుండా ఎండుటాకులు లేదా కొబ్బరి పొట్టు పరచండి."
            ],
            "speech": "మొక్కలకు ఉదయాన్నే నీరు పోయండి. మట్టిని వేలితో తాకి తేమ లేనప్పుడు మాత్రమే నీరు పెట్టండి.",
            "tips": "కృషినోవా యాప్‌లో వర్ష సూచన చూసుకోండి; వర్షం పడే అవకాశం ఉంటే నీరు ఆపండి."
        }
    },
    "pests": {
        "keywords": ["pest", "insect", "aphids", "worm", "कीड़े", "कीट", "माखी", "જીવાત", "કીડા", "పురుగులు", "తేనెమంచు", "మకట్ట", "spray", "neem"],
        "en": {
            "topic": "Urban Organic Pest & Insect Management",
            "summary": "Aphids, whiteflies, and spider mites commonly infest balcony tomatoes and chillies.",
            "steps": [
                "1. Water Jet: Spray leaf undersides with a forceful water mist stream to dislodge pests.",
                "2. Organic Neem Oil: Mix 5ml pure cold-pressed neem oil and 2ml baby shampoo in 1 liter lukewarm water. Shake well and spray every 7 days.",
                "3. Yellow Sticky Traps: Hang a small yellow sticky card nearby to trap flying whiteflies.",
                "4. Companion Planting: Grow marigold (Genda) or mint pots alongside to naturally repel insects."
            ],
            "speech": "Control pests naturally using neem oil spray. Mix five milliliters of neem oil with a drop of liquid soap in one liter of water and spray on the underside of leaves once a week.",
            "tips": "Always spray neem solution either at sunrise or sunset to avoid burning leaf foliage."
        },
        "gu": {
            "topic": "શાકભાજીમાં દેશી જીવાત અને કીટક નિયંત્રણ",
            "summary": "મરચી, ટામેટા અને રીંગણમાં સફેદ માખી, મોલો-મસી અને ઈયળ સામાન્ય છે.",
            "steps": [
                "૧. પાણીનો ફુવારો: પાંદડાની નીચે જોરથી પાણી છાંટીને જીવાતને દૂર કરો.",
                "૨. લીમડાનું તેલ સ્પ્રે: ૧ લિટર નવશેકા પાણીમાં ૫ મિ.લી. લીમડાનું તેલ અને ૨ મિ.લી. લિક્વિડ સાબુ મેળવી હલાવીને દર ૭ દિવસે સાંજે છાંટો.",
                "૩. પીળા ચીકણા ટ્રેપ: કૂંડા નજીક પીળું સ્ટીકી પેપર લગાવો જેથી માખીઓ ચોંટી જાય.",
                "૪. ગલગોટા વાવો: કૂંડાની બાજુમાં ગલગોટા (હજારીગલ) નો છોડ વાવવાથી જીવાત આપમેળે દૂર રહે છે."
            ],
            "speech": "જીવાત દૂર કરવા માટે લીમડાના તેલનો દેશી પ્રયોગ કરો. એક લિટર પાણીમાં પાંચ મિલી લીમડાનું તેલ મેળવી અઠવાડિયે એક વાર પાંદડાની નીચે સાંજે છંટકાવ કરો.",
            "tips": "છંટકાવ હંમેશા સવારે વહેલા અથવા સૂર્યાસ્ત પછી જ કરવો જેથી પાંદડા બળે નહીં."
        },
        "hi": {
            "topic": "घरेलू जैविक कीट एवं कीड़ा नियंत्रण",
            "summary": "बालकनी के मिर्च, टमाटर और बैंगन में माहू (एफिड्स), सफेद मक्खी और मकड़ी कीट आम होते हैं।",
            "steps": [
                "1. पानी की तेज फुहार: पत्तियों के नीचे पानी का तेज स्प्रे करें जिससे कीड़े धुल जाएं।",
                "2. नीम तेल का घोल: 1 लीटर हल्के गुनगुने पानी में 5ml नीम का तेल और 2ml तरल साबुन मिलाकर हर 7 दिन में शाम को छिड़कें।",
                "3. पीला स्टिकी ट्रैप: गमलों के पास पीला चिपचिपा कार्ड लगाएं, जिससे उड़ने वाले कीड़े चिपक जाएं।",
                "4. गेंदे का पौधा: सब्जियों के साथ गेंदा (मैरीगोल्ड) लगाएं; इसकी महक से कीड़े दूर भागते हैं।"
            ],
            "speech": "कीड़ों से बचाव के लिए 1 लीटर पानी में 5 मिलीलीटर नीम तेल और थोड़ा साबुन मिलाकर हफ्ते में एक बार पत्तियों के नीचे छिड़काव करें।",
            "tips": "नीम के तेल का छिड़काव हमेशा सुबह जल्दी या शाम को करें ताकि तेज धूप से पत्तियां न जलें।"
        },
        "te": {
            "topic": "సేంద్రీయ పురుగుల మరియు తెగుళ్ల నివారణ",
            "summary": "టమోటా, మిరప మొక్కలలో పేనుబంక, తెల్లదోమ మరియు నల్లి పురుగులు ఎక్కువగా వస్తాయి.",
            "steps": [
                "1. నీటి చిలకరింపు: ఆకుల అడుగు భాగాన నీటితో బలంగా స్ప్రే చేసి పురుగులను కడగండి.",
                "2. వేప నూనె మిశ్రమం: 1 లీటరు గోరువెచ్చని నీటిలో 5ml వేప నూనె, 2ml లిక్విడ్ సబ్బు కలిపి ప్రతి 7 రోజులకు సాయంత్రం పిచికారీ చేయండి.",
                "3. పసుపు రంగు జిగురు అట్టలు: మొక్కల దగ్గర పసుపు స్టిక్కర్ కార్డ్స్ పెడితే తెల్లదోమలు అతుక్కుంటాయి.",
                "4. బంతి మొక్కలు: కుండీల పక్కన బంతి మొక్కలు నాటితే సహజంగా పురుగులు రావు."
            ],
            "speech": "పురుగులను అరికట్టడానికి వేప నూనె ద్రావణాన్ని వారానికి ఒకసారి ఆకుల కింద పిచికారీ చేయండి. సాయంత్రం వేళల్లోనే స్ప్రే చేయండి.",
            "tips": "మొక్కల ఆకులు మాడిపోకుండా ఉండటానికి ఎల్లప్పుడూ ఉదయం లేదా సాయంత్రం మాత్రమే స్ప్రే చేయాలి."
        }
    },
    "fertilizer": {
        "keywords": ["fertilizer", "compost", "manure", "khad", "खाद", "પોષણ", "ખાતર", "ఎరువు", "పోషకాలు", "vermicompost", "growth", "flower"],
        "en": {
            "topic": "Organic Nutrients & Balanced Fertilizing",
            "summary": "Container vegetables exhaust soil nutrients quickly and need regular organic feeding.",
            "steps": [
                "1. Vermicompost: Top-dress containers with 2 handfuls of rich vermicompost every 20 days.",
                "2. Calcium for Tomatoes: Add crushed eggshells or lime powder to potting soil to prevent blossom-end rot.",
                "3. Flowering Boost: Feed liquid mustard cake extract or banana peel compost tea once a month for profuse blooms.",
                "4. Wood Ash: A pinch of wood ash adds natural potassium for sweeter and crispier fruits."
            ],
            "speech": "Feed your container plants two handfuls of vermicompost every twenty days. For tomatoes and chillies, add banana peel tea and crushed eggshells for calcium.",
            "tips": "Always loosen the top 1 inch of soil before adding compost, then water lightly."
        },
        "gu": {
            "topic": "કૂંડા માટે શ્રેષ્ઠ દેશી અને જૈવિક ખાતર",
            "summary": "કૂંડાની માટીમાંથી પોષક તત્વો ઝડપથી વપરાઈ જાય છે, તેથી નિયમિત દેશી ખાતર જરૂરી છે.",
            "steps": [
                "૧. વર્મીકમ્પોસ્ટ (અળસિયાનું ખાતર): દર ૨૦ દિવસે દરેક કૂંડામાં ૨ મુઠ્ઠી વર્મીકમ્પોસ્ટ નાખો.",
                "૨. કેલ્શિયમ માટે: ટામેટાના તળિયે કાળા ડાઘા રોકવા માટે ઈંડાની છાલનો ભૂકો અથવા થોડો ચૂનો ઉમેરો.",
                "૩. ફૂલ-ફળ વધારવા: કેળાની છાલનું પ્રવાહી ખાતર અથવા સરસવની ખોળનું પાણી મહિનામાં એકવાર આપો.",
                "૪. લાકડાની રાખ: થોડી લાકડાની રાખ ઉમેરવાથી પોટાશ મળે છે અને ફળ મજબૂત બને છે."
            ],
            "speech": "કૂંડાના છોડને દર વીસ દિવસે બે મુઠ્ઠી અળસિયાનું ખાતર આપો. ટામેટા અને મરચીમાં ફૂલ વધારવા કેળાની છાલનું પાણી ઉત્તમ છે.",
            "tips": "ખાતર નાખતા પહેલા કૂંડાની ઉપરની માટી હળવેથી ગોડવી લેવી અને પછી હળવું પાણી આપવું."
        },
        "hi": {
            "topic": "गमलों के लिए सर्वश्रेष्ठ जैविक खाद",
            "summary": "गमलों की सीमित मिट्टी में पोषक तत्व जल्दी खत्म होते हैं, इसलिए हर महीने जैविक खाद देना जरूरी है।",
            "steps": [
                "1. केंचुआ खाद (वर्मीकम्पोस्ट): हर 20 दिन में पौधे की जड़ के पास 2 मुट्ठी वर्मीकम्पोस्ट डालें।",
                "2. टमाटर के लिए कैल्शियम: फल सड़न (ब्लॉसम एंड रॉट) से बचाने के लिए अंडे के छिलकों का पाउडर या चुटकी भर चूना डालें।",
                "3. फल-फूल की वृद्धि: केले के छिलके का पानी या सरसों की खली का तरल खाद महीने में एक बार दें।",
                "4. लकड़ी की राख: थोड़ी सी लकड़ी की राख पोटाश का सबसे अच्छा प्राकृतिक स्रोत है।"
            ],
            "speech": "पौधों को हर 20 दिन में 2 मुट्ठी वर्मीकम्पोस्ट दें। टमाटर और मिर्च में फूल-फल बढ़ाने के लिए केले के छिलके की खाद बहुत लाभकारी है।",
            "tips": "खाद डालने से पहले गमले की 1 इंच मिट्टी की हल्की गुड़ाई करें, फिर थोड़ा पानी दें।"
        },
        "te": {
            "topic": "కుండీ మొక్కలకు సేంద్రియ పోషకాలు & ఎరువులు",
            "summary": "కుండీలలోని పరిమిత మట్టిలో బలం త్వరగా తగ్గుతుంది, కాబట్టి ప్రతి 20 రోజులకు సేంద్రియ ఎరువు వేయాలి.",
            "steps": [
                "1. వర్మీ కంపోస్ట్ (వానపాముల ఎరువు): ప్రతి 20 రోజులకు మొక్క మొదట్లో 2 గుప్పిళ్ల వర్మీ కంపోస్ట్ వేయండి.",
                "2. కాల్షియం పోషకం: టమోటాల కాయల కుళ్లు నివారణకు గుడ్డు పెంకుల పొడి లేదా కొద్దిగా సున్నం కలపండి.",
                "3. పూత, కాత కోసం: అరటి తొక్కల రసం లేదా ఆవపిండి ద్రావణాన్ని నెలకు ఒకసారి మొక్క మొదట్లో పోయండి.",
                "4. బూడిద: కొద్దిగా కట్టెల బూడిద వేస్తే సహజ పొటాష్ అంది కాయలు పెద్దవిగా వస్తాయి."
            ],
            "speech": "మొక్కలకు ప్రతి 20 రోజులకు రెండు గుప్పిళ్ల వానపాముల ఎరువు వేయండి. పూత రాలకుండా అరటి తొక్కల ద్రావణం వాడండి.",
            "tips": "ఎరువు వేసే ముందు మట్టిని గుల్లగా చేసి, ఎరువు వేసిన తర్వాత కొద్దిగా నీరు పోయండి."
        }
    }
}


def clarify_doubt(query_text, language="en"):
    """
    Clarifies a user's agricultural/urban farming question in the requested language
    (English, Gujarati, Hindi, Telugu). Returns formatted answer and speech text.
    """
    lang = (language or "en").lower().strip()
    if lang not in SUPPORTED_LANGUAGES:
        lang = "en"

    query = (query_text or "").strip().lower()
    meta = SUPPORTED_LANGUAGES[lang]

    # Match best domain topic based on query keywords
    matched_topic_key = None
    for top_key, topic_data in KNOWLEDGE_TOPICS.items():
        for kw in topic_data["keywords"]:
            if kw.lower() in query:
                matched_topic_key = top_key
                break
        if matched_topic_key:
            break

    # If matched, generate tailored structured response
    if matched_topic_key and matched_topic_key in KNOWLEDGE_TOPICS:
        t_data = KNOWLEDGE_TOPICS[matched_topic_key][lang]
        response = {
            "success": True,
            "language": lang,
            "speech_locale": meta["speech_locale"],
            "detected_topic": t_data["topic"],
            "summary": t_data["summary"],
            "action_steps": t_data["steps"],
            "tips": t_data["tips"],
            "speech_text": t_data["speech"],
            "followup_questions": meta["sample_questions"][:3]
        }
        return response

    # Dynamic fallback based on language for general urban farming queries
    fallbacks = {
        "en": {
            "topic": "Urban Gardening Care Advice",
            "summary": f"KrishiNova advice for your question: '{query_text}'",
            "steps": [
                "1. Sunlight Check: Most vegetables (tomato, pepper, brinjal) require 6 hours of direct sun daily.",
                "2. Drainage: Ensure pots have drainage holes so stagnant water does not cause root rot.",
                "3. Hydration: Water early in the morning when the top 1 inch of potting soil feels dry.",
                "4. Organic Care: Apply a light foliar spray of organic neem oil (5ml/L) once every 10 days for pest deterrence."
            ],
            "speech": f"For your question about {query_text[:50]}, make sure your plant gets six hours of sunlight, water early in the morning, and ensure the pot drains well.",
            "tips": "You can also upload a leaf photo to KrishiNova's MobileNetV2 scanner for instant disease diagnosis."
        },
        "gu": {
            "topic": "કૃષિનોવા બાગાયત સલાહ",
            "summary": f"તમારા પ્રશ્ન માટે કૃષિનોવા AI માર્ગદર્શન: '{query_text}'",
            "steps": [
                "૧. સૂર્યપ્રકાશ: ટામેટા, મરચી અને રીંગણ જેવા શાકભાજીને દરરોજ ૬ કલાક સીધો તડકો જોઈએ.",
                "૨. પાણીનો નિકાલ: કૂંડાના તળિયે કાણું હોવું જરૂરી છે જેથી પાણી ભરાઈ રહેવાથી મૂળ સડે નહીં.",
                "૩. પાણી આપવાનો સમય: સવારે વહેલા પાણી આપો, જ્યારે ઉપરની ૧ ઇંચ માટી સૂકી જણાય.",
                "૪. રોગ-જીવાત રક્ષણ: દર ૧૦ દિવસે લીમડાના તેલનો (૧ લિટરમાં ૫ મિલી) સવારે છંટકાવ કરો."
            ],
            "speech": f"તમારા સવાલ માટે સલાહ: છોડને ૬ કલાક તડકો આપો, સવારે પાણી આપો અને કૂંડામાંથી પાણીનો સારો નિકાલ રાખો.",
            "tips": "તમે કૃષિનોવા એપમાં પાંદડાનો ફોટો અપલોડ કરીને પણ રોગની ચોક્કસ તપાસ કરી શકો છો."
        },
        "hi": {
            "topic": "कृषिनोवा बागवानी एवं फसल सलाह",
            "summary": f"आपके प्रश्न के लिए कृषिनोवा AI मार्गदर्शन: '{query_text}'",
            "steps": [
                "1. धूप की जांच: अधिकांश सब्जियों (टमाटर, मिर्च, बैंगन) को रोजाना कम से कम 6 घंटे सीधी धूप चाहिए।",
                "2. जल निकासी: गमले में जल निकासी छेद खुला रखें ताकि पानी रुकने से जड़ें न सड़ें।",
                "3. सिंचाई नियम: सुबह जल्दी पानी दें जब ऊपरी 1 इंच मिट्टी छूने पर सूखी लगे।",
                "4. जैविक सुरक्षा: कीटों से बचाव के लिए हर 10 दिन में नीम के तेल (5ml/लीटर) का छिड़काव करें।"
            ],
            "speech": f"आपके प्रश्न के लिए सलाह: पौधे को 6 घंटे धूप दें, सुबह जल्दी पानी डालें और गमले में जल निकासी का ध्यान रखें।",
            "tips": "आप कृषिनोवा में पत्ती की फोटो अपलोड करके भी बीमारी की तुरंत जांच कर सकते हैं।"
        },
        "te": {
            "topic": "కృషినోవా వ్యవసాయ సలహా",
            "summary": f"మీ ప్రశ్నకు కృషినోవా AI సమాధానం: '{query_text}'",
            "steps": [
                "1. ఎండ అవసరం: కూరగాయల మొక్కలకు (టమోటా, మిరప, వంగ) రోజుకు కనీసం 6 గంటల ప్రత్యక్ష ఎండ అవసరం.",
                "2. నీటి పారుదల: కుండీ అడుగున నీరు నిల్వ ఉండకుండా రంధ్రం సరిగ్గా ఉండేలా చూడండి.",
                "3. నీరు పోసే సమయం: ఉదయం వేళల్లో మాత్రమే పై మట్టి ఆరినప్పుడు నీరు పోయాలి.",
                "4. సహజ రక్షణ: పురుగులు రాకుండా ప్రతి 10 రోజులకు ఒకసారి వేప నూనె (5ml/లీటర్) స్ప్రే చేయండి."
            ],
            "speech": f"మీ సందేహానికి సమాధానం: మొక్కకు 6 గంటల ఎండ తగిలేలా చూడండి, ఉదయాన్నే నీరు పోయండి మరియు నీరు నిలవకుండా చూసుకోండి.",
            "tips": "మీరు కృషినోవాలో ఆకు ఫోటో తీసి అప్‌లోడ్ చేయడం ద్వారా కూడా తెగుళ్లను గుర్తించవచ్చు."
        }
    }

    fallback = fallbacks[lang]
    return {
        "success": True,
        "language": lang,
        "speech_locale": meta["speech_locale"],
        "detected_topic": fallback["topic"],
        "summary": fallback["summary"],
        "action_steps": fallback["steps"],
        "tips": fallback["tips"],
        "speech_text": fallback["speech"],
        "followup_questions": meta["sample_questions"][:3]
    }


def get_language_metadata(lang_code="en"):
    """Returns metadata (native name, speech locale, sample questions) for a language."""
    code = (lang_code or "en").lower().strip()
    return SUPPORTED_LANGUAGES.get(code, SUPPORTED_LANGUAGES["en"])
