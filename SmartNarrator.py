import random

class SmartNarrator:
    def __init__(self):
        self.synonyms = {
            "person": ["a person", "someone", "a pedestrian", "an individual", 
                "a passerby", "a human", "somebody", "a friend"],
            "bicycle": ["a bicycle", "a bike", "a cyclist", "a bike rider", "a cyclist", "a bike rider"],
            "car": ["a car", "a vehicle", "an automobile", "a sedan", "a motorcar"],
            "motorcycle": ["a motorcycle", "a motorbike", "a motor cycle"],
            "bus": ["a bus", "a large vehicle", "public transport", "a coach"],
            "truck": ["a truck", "a lorry", "a heavy vehicle", "a pickup truck", "a van"],
            "traffic light": ["a traffic light", "a traffic signal", "a traffic lamp", "a traffic indicator", "a stoplight", "the traffic lights"],
            "fire hydrant": ["a fire hydrant", "a hydrant", "a fire plug"],
            "stop sign": ["a stop sign", "a traffic sign"],
            "bench": ["a bench", "a seat", "outdoor seating", "a place to sit", "a public seat"]
        }

        self.templates = {
            "critical": [ # < 60cm (Immediate / Personal Space)
                "{label} is right in front of you, {dist} away.",
                "You are right next to {label}.",
                "There is {label} immediately {pos}.",
                "Very close {pos}, I see {label}.",
                "Just so you know, {label} is within arm's reach.",
                "{label} is directly in your path, {dist} away.",
                "You are standing very close to {label}.",
                "Just {dist} from you is {label}.",
                "{pos}, there is {label}.",
                "For your info, {label} is just {dist} away.",
                "{label} is here {pos}.",
                "Immediate proximity: {label} is {dist} away.",
                "You have reached {label}.",
                "{label} is extremely close to you.",
                "Check {pos}, {label} is right there.",
                "Detected {label} at close range, {dist}.",
                "You are just about to reach {label}.",
                "{label} is {dist} from your position.",
                "Heads up, {label} {pos} is very close.",
                "Close contact: {label} is {dist} away.",
                "{label} is immediately ahead.",
                "Be mindful of {label} {pos}.",
                "You are just {dist} away from {label}.",
                "Please note, {label} is right there.",
                "Directly {pos}, {label} is close.",
                "FYI: {label} is {dist} away.",
                "You are nearly touching {label}.",
                "Just a heads up, {label} is right here.",
                "Note that {label} is immediately {pos}.",
                "Right in front: {label}, {dist}.",
                "There is {label} right next to you.",
                "Your path has {label} {dist} away.",
                "You are face to face with {label}.",
                "{label} is occupying your immediate space.",
                "{label} {pos} is very close.",
                "It looks like {label} is right there.",
                "Verify {pos}, {label} is extremely close.",
                "{label} is just {dist} from you.",
                "Object {pos}: {label}.",
                "Close quarters with {label}.",
                "You are within {dist} of {label}.",
                "{label} is practically touching you.",
                "Right ahead, {label} is {dist} away.",
                "Very close range: {label}.",
                "You're close to {label}, {dist}.",
                "Just be aware, {label} is {pos}.",
                "{label} is directly in front of you.",
                "Immediate {label} detected {pos}.",
                "You are right beside {label}.",
                "Close up: {label} is {dist} away.",
                "Looks like you found {label}.",
                "{label} is {pos}, {dist}."
            ],
            "warning": [ # 60cm - 200cm (Navigation / Approach)
                "There is {label} {pos}, about {dist} away.",
                "Be careful, {label} is {pos}.",
                "Navigating. I see {label} {pos}, {dist}.",
                "Heads up, {label} detected {dist} ahead.",
                "You are approaching {label} {pos}.",
                "Note that {label} is {dist} from you.",
                "Keep an eye out for {label} {pos}.",
                "Awareness check: {label} is nearby.",
                "{label} detected {pos}, distance is {dist}.",
                "Path update: {label} is {dist} away.",
                "Approaching {label} {pos}, {dist} away.",
                "There is {label} {pos}, about {dist}.",
                "{label} detected {pos}, {dist} ahead.",
                "You are getting closer to {label}.",
                "About {dist} ahead, there is {label}.",
                "Keep an eye out for {label} {pos}.",
                "Navigating towards {label}, {dist} away.",
                "{label} is coming up {pos}.",
                "Detected {label} {pos} in your path.",
                "Note {label} roughly {dist} ahead.",
                "Be aware of {label} {pos}, {dist}.",
                "Scanning {label} {pos}, {dist} away.",
                "You are walking towards {label}.",
                "{label} found {pos}, moderate distance.",
                "Upcoming: {label} is {dist} away.",
                "Prepare for {label} {pos}.",
                "Path update: {label} is {dist} out.",
                "I see {label} {pos}, getting closer.",
                "{label} is located {dist} ahead.",
                "Your path has {label} {pos}.",
                "Look out for {label} {dist} away.",
                "Sensor reads {label} {pos}, {dist}.",
                "Continuing towards {label}.",
                "Within range: {label} is {dist}.",
                "Closing in on {label}, {dist}.",
                "Steady, {label} is {pos}.",
                "Object ahead: {label}, {dist}.",
                "Walking path contains {label} {pos}.",
                "Moderate distance to {label}.",
                "Expect {label} in {dist}.",
                "Nearby object: {label} {pos}.",
                "Short distance to {label}.",
                "You will soon reach {label}.",
                "Attention, {label} is {dist} ahead.",
                "Please note {label} is {pos}.",
                "Tracked {label} {pos} at {dist}.",
                "Be advised, {label} is nearby.",
                "Navigation alert: {label} {pos}.",
                "Moving towards {label}.",
                "Mid-range detection: {label}."
            ],
            "info": [ # 200cm - 400cm (Mid-Range / Visible Ahead)
                "I see {label} {pos} ahead.",
                "There is {label} further down the path.",
                "Visible ahead: {label}.",
                "You are approaching {label}, currently {dist} away.",
                "About {dist} out, there is {label}.",
                "Look {pos}, {label} is ahead.",
                "{label} detected {dist} down the way.",
                "In front of you {pos}, I see {label}.",
                "Straight ahead {pos}, there is {label}.",
                "Walking path check: {label} is {dist} away.",
                "Medium distance: {label} {pos}.",
                "Scanning ahead: {label} detected.",
                "Keep going, {label} is {dist} ahead.",
                "{label} is in your general direction {pos}.",
                "You will eventually reach {label}.",
                "Further out {pos}, I detect {label}.",
                "There is {label} sitting {dist} away.",
                "Up ahead, {label} is visible.",
                "Not too far {pos}, there is {label}.",
                "Moderate distance to {label} {pos}.",
                "Ahead {pos}, {label} is waiting.",
                "Path clear until {label}, {dist} away.",
                "Visual contact: {label} {pos} ahead.",
                "Be aware of {label} further out.",
                "{label} is positioned {dist} from you.",
                "Standard range: {label} detected.",
                "Looking down the path, I see {label}.",
                "{label} is visible {pos}, {dist}.",
                "Continue forward, {label} is {dist} out.",
                "Mid-range detection of {label}.",
                "Target ahead: {label} {pos}.",
                "Spotting {label} {dist} in front.",
                "There's {label} up the road {pos}.",
                "Visible object {pos}: {label}.",
                "Detected {label} at a moderate distance.",
                "Forward view shows {label}.",
                "{label} is {dist} ahead of your position.",
                "See {label} {pos} ahead.",
                "Advancing towards {label}.",
                "Ahead: {label} at {dist}.",
                "Your trajectory leads to {label}.",
                "{label} spotted mid-range.",
                "Within sight: {label} {pos}.",
                "Relevant object ahead: {label}.",
                "Keep walking towards {label}."
            ],
            "unknown": [ # > 400cm OR 999 (Far Range / 5m+ range)
                "There is {label} further ahead.",
                "I see {label} over there {pos}.",
                "{label} is located further down the path.",
                "Past the immediate area, there is {label}.",
                "Looking ahead, I spot {label}.",
                "{label} is visible a bit further away.",
                "I detect {label} beyond 4 meters.",
                "Further out {pos}, I see {label}.",
                "There is {label} down the way.",
                "Visual detection: {label} is further out.",
                "{label} is positioned further ahead.",
                "I see {label} in the distance.",
                "Walking path shows {label} further up.",
                "Beyond your current range, there is {label}.",
                "{label} detected further away.",
                "It looks like {label} is over there.",
                "I can see {label} past the near zone.",
                "There is {label} sitting further back.",
                "Detected {label} at a longer distance.",
                "{label} is visible ahead, but not close.",
                "Checking further out: {label} found.",
                "I see {label} {pos}, further away.",
                "That is {label} over there.",
                "Just down the road, I see {label}.",
                "{label} is past the immediate sensors.",
                "Visuals show {label} further ahead.",
                "There is {label} well ahead of you.",
                "Keep going, {label} is further out.",
                "I spot {label} in the wider area.",
                "Not close, but I see {label} {pos}.",
                "{label} is visible at a distance.",
                "Further {pos}, there is {label}.",
                "Scanning deeper: {label} detected.",
                "You are heading towards {label} further out.",
                "Path ahead contains {label}.",
                "{label} is outside immediate range.",
                "Looking past the near objects, I see {label}.",
                "There is {label} a bit of a distance away.",
                "I see {label}, it's further down.",
                "Safe distance: {label} detected ahead.",
                "{label} is visible beyond the 4 meter mark.",
                "Over there {pos}, {label} is visible.",
                "I see {label} ahead, no immediate obstruction.",
                "Clear for now, but {label} is further up.",
                "{label} detected, it's a bit far.",
                "Visual confirmed on {label} further away.",
                "That looks like {label} over there.",
                "Further along the path: {label}.",
                "I see {label} standing back there.",
                "Detected {label} outside close range."
            ]
        }


    def get_label_synonym(self, raw_label):
        options = self.synonyms.get(raw_label.lower(), [f"a {raw_label}"])
        return random.choice(options)

    def get_position_text(self, center_x):
        if center_x < 0.35:
            return "on your left"
        elif center_x > 0.65:
            return "on your right"
        else:
            return "right ahead"

    def generate(self, label, distance_cm, center_x):
        if distance_cm < 60:
            category = "critical"
            dist_str = f"{distance_cm:.0f} centimeters"
        elif distance_cm < 200:
            category = "warning"
            dist_str = f"{distance_cm:.0f} centimeters"
        elif distance_cm < 400:
            category = "info" 
            dist_str = f"{int(distance_cm/100)} meters" 
        else: 
            category = "unknown"
            dist_str = ""

        template = random.choice(self.templates[category])
        natural_label = self.get_label_synonym(label)
        pos_str = self.get_position_text(center_x)
        sentence = template.format(label=natural_label, dist=dist_str, pos=pos_str)
        
        return " ".join(sentence.split())