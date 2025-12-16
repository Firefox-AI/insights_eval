SYSTEM_PROMPT_PERSONA_CREATION = """
You are tasked to create a complex persona based on a few basic persona given to you.
You should return a name and a description of this new persona details.
The output should include:
1. A name of this new person
2. A detail description of the new persona
3. Some behaviour or hobby instances that can help people understand more about this person.

Output format:
{
    "name": "A name of this new person",
    "persona_detail_description": "A detail description of the new persona",
    "behaviour_or_hobby_instances": ["hobby 1", "hobby 2", ...]
}

"""

USER_PROMPT_PERSONA_CREATION = """
Given basic persona:
"""



SYSTEM_PROMPT_CATEGORY_INTENT = """
You are tasked to find out all the relevant (category, intent) pairs of a given persona.

VALID_CATEGORIES = [
  "Arts & Entertainment",
  "Autos & Vehicles",
  "Beauty & Fitness",
  "Books & Literature",
  "Business & Industrial",
  "Computers & Electronics",
  "Food & Drink",
  "Games",
  "Hobbies & Leisure",
  "Home & Garden",
  "Internet & Telecom",
  "Jobs & Education",
  "Law & Government",
  "News",
  "Online Communities",
  "People & Society",
  "Pets & Animals",
  "Real Estate",
  "Reference",
  "Science",
  "Shopping",
  "Sports",
  "Travel & Transportation",
]

VALID_INTENTS = {
  "Research / Learn": "User is seeking new information, understanding, explanations, or background knowledge about a topic.",
  "Compare / Evaluate": "User is assessing differences, pros/cons, quality, or suitability between multiple options.",
  "Plan / Organize": "User is structuring future actions, logistics, schedules, or decisions.",
  "Buy / Acquire": "User intends to purchase, order, or obtain a product, service, or resource.",
  "Create / Produce": "User is trying to make something or generate original output, either physical or digital.",
  "Communicate / Share": "User intends to interact with others, exchange information, or post/share content.",
  "Monitor / Track": "User is checking updates, status changes, progress, or real-time information.",
  "Entertain / Relax": "User is engaging in leisure or recreation without a goal beyond enjoyment.",
  "Resume / Revisit": "User is returning to previously viewed or ongoing content, tasks, or activities.",
}

Example:

Input persona:
{
  "name": "Avery Lin",
  "description": "Avery Lin is a methodical, tech-forward community organizer who blends competitive PC gaming with spatial design, travel hacking, and hands-on making. Weekdays, Avery freelances as an interior decor planner for small apartments and pop-up shops, using LiDAR scans and SketchUp to deliver ergonomic layouts, mood boards, and sourcing lists. Evenings, they optimize a compact SFF gaming rig, follow hardware benchmarks, and swap tips on forums and Discord. Weekends center on a local makerspace, where Avery runs craft and 3D-printing workshops, curates beginner-friendly supply kits, and keeps meticulous safety and BOM checklists. Planning is their superpower: a Notion dashboard connects trip itineraries and price-tracking sheets to decor palettes, printer profiles, and workshop calendars. Avery saves cooking videos for destination-inspired meals, often recreating dishes on the road or at home and 3D-printing custom kitchen helpers. Decision-making is data-driven and iterative, from A/B testing lighting layouts and print settings to monitoring flight alerts and GPU price histories. They value clean aesthetics, ergonomic function, and budget-conscious sustainability, and they host cross-community events like LAN nights paired with print-and-paint sessions. Tools of choice include Google Flights and ITA Matrix, OctoPrint and PrusaSlicer, SketchUp and Canva, a color-calibrated monitor, and an iPad with LiDAR. Goals include publishing downloadable STL decor kits, growing an Etsy side hustle, and pairing design-focused city trips with gaming conventions.",
  "example_behaviours": [
    "Builds and tunes a compact ITX gaming PC, undervolts the GPU, creates custom fan curves, and posts benchmark comparisons to forums",
    "Hosts ranked FPS nights and reviews VODs to analyze crosshair placement, utility timing, and map control",
    "Tracks GPU, SSD, and monitor prices in a shared spreadsheet and pings friends when deals match performance targets",
    "Uses ITA Matrix filters and Google Flights alerts to assemble multi-city itineraries that align with design museums and gaming events",
    "Designs small-apartment layouts with SketchUp, validates measurements via LiDAR scans, and creates mood boards with costed sourcing lists",
    "3D-prints functional decor like cable raceways, wall planters, and custom light switch plates matched to room color palettes",
    "Runs monthly Intro to 3D Printing workshops, teaching slicing basics, material selection, safety, and maintenance routines",
    "Queues prints via OctoPrint for overnight runs, performs PID tuning and flow calibration, and logs successful profiles in Notion",
    "Watches cooking channels and compiles a recipe library tagged by cuisine and destination, then recreates dishes during trips",
    "Designs and prints food-adjacent tools such as cookie cutters and spice jar labels, noting food-safety liners and finishing steps",
    "Maintains a travel EDC kit with universal adapter, travel router, cable organizers, and 3D-printed cable winders",
    "Curates a decor sample kit with paint swatches, bulb temperature options, and a compact measuring set for on-site client consults",
    "Moderates a makers-and-gamers Discord, writes onboarding guides, runs polls for workshop topics, and schedules event reminders",
    "Publishes Etsy listings for minimal desk organizers and plant stands, A/B testing photos, titles, and print finishes",
    "Creates one-page city guides with transit tips, local SIM options, coworking spaces, and must-try street foods",
    "Time-blocks Sundays for CAD practice, batch meal prep inspired by saved videos, and a competitive gaming session"
  ]
}

Expected output:
[
  ["Computers & Electronics", "Research / Learn"],
  ["Computers & Electronics", "Compare / Evaluate"],
  ["Computers & Electronics", "Monitor / Track"],
  ["Computers & Electronics", "Buy / Acquire"],
  ["Computers & Electronics", "Create / Produce"],
  ["Computers & Electronics", "Communicate / Share"],
  ["Computers & Electronics", "Resume / Revisit"],

  ["Games", "Entertain / Relax"],
  ["Games", "Research / Learn"],
  ["Games", "Monitor / Track"],
  ["Games", "Compare / Evaluate"],
  ["Games", "Create / Produce"],
  ["Games", "Communicate / Share"],
  ["Games", "Resume / Revisit"],

  ["Hobbies & Leisure", "Create / Produce"],
  ["Hobbies & Leisure", "Research / Learn"],
  ["Hobbies & Leisure", "Buy / Acquire"],
  ["Hobbies & Leisure", "Plan / Organize"],
  ["Hobbies & Leisure", "Communicate / Share"],

  ["Home & Garden", "Plan / Organize"],
  ["Home & Garden", "Research / Learn"],
  ["Home & Garden", "Create / Produce"],
  ["Home & Garden", "Buy / Acquire"],
  ["Home & Garden", "Compare / Evaluate"],

  ["Shopping", "Compare / Evaluate"],
  ["Shopping", "Buy / Acquire"],
  ["Shopping", "Research / Learn"],
  ["Shopping", "Plan / Organize"],

  ["Travel & Transportation", "Plan / Organize"],
  ["Travel & Transportation", "Monitor / Track"],
  ["Travel & Transportation", "Buy / Acquire"],
  ["Travel & Transportation", "Research / Learn"],

  ["Arts & Entertainment", "Research / Learn"],
  ["Arts & Entertainment", "Entertain / Relax"],
  ["Arts & Entertainment", "Create / Produce"],
  ["Arts & Entertainment", "Compare / Evaluate"],

  ["Online Communities", "Communicate / Share"],
  ["Online Communities", "Monitor / Track"],
  ["Online Communities", "Create / Produce"],
  ["Online Communities", "Resume / Revisit"],

  ["Internet & Telecom", "Plan / Organize"],
  ["Internet & Telecom", "Create / Produce"],
  ["Internet & Telecom", "Communicate / Share"],
  ["Internet & Telecom", "Research / Learn"],

  ["Jobs & Education", "Create / Produce"],
  ["Jobs & Education", "Research / Learn"],
  ["Jobs & Education", "Plan / Organize"],

  ["Reference", "Research / Learn"],
  ["Reference", "Resume / Revisit"],
  ["Reference", "Monitor / Track"],

  ["Science", "Research / Learn"],
  ["Science", "Monitor / Track"],

  ["Business & Industrial", "Research / Learn"],
  ["Business & Industrial", "Create / Produce"],
  ["Business & Industrial", "Compare / Evaluate"],

  ["Real Estate", "Research / Learn"],
  ["Real Estate", "Plan / Organize"],

  ["Food & Drink", "Create / Produce"],
  ["Food & Drink", "Research / Learn"],

  ["People & Society", "Communicate / Share"],
  ["People & Society", "Plan / Organize"]
]
"""


USER_PROMPT_CATEGORY_INTENT = """
Input persona:
{}
"""


SYSTEM_PROMPT_INSIGHTS_FROM_PERSONA = """
You are tasked to find out all the relevant relevant insights of a given persona, and return those in a list.
An insight must include 'insight_summary', 'category', 'intent', and a 'score'
- insight_summary: a concise phrase captured from the persona descriptions or behaviours
- category: the valid category of this insight
- intent: the valid intent of this insight
- score: how relevant is this insight to the persona, ranged from 1 to 5


VALID_CATEGORIES = [
  "Arts & Entertainment",
  "Autos & Vehicles",
  "Beauty & Fitness",
  "Books & Literature",
  "Business & Industrial",
  "Computers & Electronics",
  "Food & Drink",
  "Games",
  "Hobbies & Leisure",
  "Home & Garden",
  "Internet & Telecom",
  "Jobs & Education",
  "Law & Government",
  "News",
  "Online Communities",
  "People & Society",
  "Pets & Animals",
  "Real Estate",
  "Reference",
  "Science",
  "Shopping",
  "Sports",
  "Travel & Transportation",
]

VALID_INTENTS = {
  "Research / Learn": "User is seeking new information, understanding, explanations, or background knowledge about a topic.",
  "Compare / Evaluate": "User is assessing differences, pros/cons, quality, or suitability between multiple options.",
  "Plan / Organize": "User is structuring future actions, logistics, schedules, or decisions.",
  "Buy / Acquire": "User intends to purchase, order, or obtain a product, service, or resource.",
  "Create / Produce": "User is trying to make something or generate original output, either physical or digital.",
  "Communicate / Share": "User intends to interact with others, exchange information, or post/share content.",
  "Monitor / Track": "User is checking updates, status changes, progress, or real-time information.",
  "Entertain / Relax": "User is engaging in leisure or recreation without a goal beyond enjoyment.",
  "Resume / Revisit": "User is returning to previously viewed or ongoing content, tasks, or activities.",
}
"""

USER_PROMPT_INSIGHTS_FROM_PERSONA = """
Input persona:
{}
"""

SYSTEM_PROMPT_QUERIES_FROM_PERSONA = """
You are tasked to generate a list of queries a given user might have in a web browswer.
You will have the persona of this user, generate 100 queries likely from this user.
The queries should be realistic. Usually a user will type in short phrases that are most relevant to what they are looking for.
The queries might just be the combination of some keywords that is not in correct grammar.
The generated queries should not be looking for the same thing with different sayings. But looking for the same item on different platform is allowed.
"""


USER_PROMPT_QUERIES_FROM_PERSONA = """
Input persona:
{}
"""


