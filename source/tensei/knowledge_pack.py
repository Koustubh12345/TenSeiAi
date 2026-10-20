"""Built-in knowledge pack: fetches a broad, curated knowledge base from
Wikipedia (plain-text extracts) straight into TenSeiAi's memory, so the model
ships with real knowledge inside it. Resumable: already-fetched titles are
remembered in the memory key-value store."""

import json
import queue
import threading
import time
from urllib.parse import quote

from . import websearch

COUNTRIES = (
    "Afghanistan, Albania, Algeria, Andorra, Angola, Argentina, Armenia, Australia, "
    "Austria, Azerbaijan, Bahrain, Bangladesh, Barbados, Belarus, Belgium, Belize, "
    "Benin, Bhutan, Bolivia, Bosnia and Herzegovina, Botswana, Brazil, Brunei, "
    "Bulgaria, Burkina Faso, Burundi, Cambodia, Cameroon, Canada, Chad, Chile, "
    "China, Colombia, Costa Rica, Croatia, Cuba, Cyprus, Czech Republic, Denmark, "
    "Dominican Republic, Ecuador, Egypt, El Salvador, Eritrea, Estonia, Ethiopia, "
    "Fiji, Finland, France, Gabon, Georgia (country), Germany, Ghana, Greece, "
    "Guatemala, Guinea, Guyana, Haiti, Honduras, Hungary, Iceland, India, Indonesia, "
    "Iran, Iraq, Ireland, Israel, Italy, Ivory Coast, Jamaica, Japan, Jordan, "
    "Kazakhstan, Kenya, Kuwait, Kyrgyzstan, Laos, Latvia, Lebanon, Liberia, Libya, "
    "Lithuania, Luxembourg, Madagascar, Malawi, Malaysia, Maldives, Mali, Malta, "
    "Mauritania, Mauritius, Mexico, Moldova, Monaco, Mongolia, Montenegro, Morocco, "
    "Mozambique, Myanmar, Namibia, Nepal, Netherlands, New Zealand, Nicaragua, "
    "Niger, Nigeria, North Korea, North Macedonia, Norway, Oman, Pakistan, Panama, "
    "Papua New Guinea, Paraguay, Peru, Philippines, Poland, Portugal, Qatar, Romania, "
    "Russia, Rwanda, Saudi Arabia, Senegal, Serbia, Seychelles, Sierra Leone, "
    "Singapore, Slovakia, Slovenia, Somalia, South Africa, South Korea, South Sudan, "
    "Spain, Sri Lanka, Sudan, Suriname, Sweden, Switzerland, Syria, Taiwan, Tajikistan, "
    "Tanzania, Thailand, Togo, Trinidad and Tobago, Tunisia, Turkey, Turkmenistan, "
    "Uganda, Ukraine, United Arab Emirates, United Kingdom, United States, Uruguay, "
    "Uzbekistan, Venezuela, Vietnam, Yemen, Zambia, Zimbabwe"
)

ELEMENTS = (
    "Hydrogen, Helium, Lithium, Beryllium, Boron, Carbon, Nitrogen, Oxygen, Fluorine, "
    "Neon, Sodium, Magnesium, Aluminium, Silicon, Phosphorus, Sulfur, Chlorine, Argon, "
    "Potassium, Calcium, Scandium, Titanium, Vanadium, Chromium, Manganese, Iron, "
    "Cobalt, Nickel, Copper, Zinc, Gallium, Germanium, Arsenic, Selenium, Bromine, "
    "Krypton, Rubidium, Strontium, Yttrium, Zirconium, Niobium, Molybdenum, "
    "Technetium, Ruthenium, Rhodium, Palladium, Silver, Cadmium, Indium, Tin, "
    "Antimony, Tellurium, Iodine, Xenon, Caesium, Barium, Lanthanum, Cerium, "
    "Praseodymium, Neodymium, Promethium, Samarium, Europium, Gadolinium, Terbium, "
    "Dysprosium, Holmium, Erbium, Thulium, Ytterbium, Lutetium, Hafnium, Tantalum, "
    "Tungsten, Rhenium, Osmium, Iridium, Platinum, Gold, Mercury (element), Thallium, "
    "Lead, Bismuth, Polonium, Astatine, Radon, Francium, Radium, Actinium, Thorium, "
    "Protactinium, Uranium, Neptunium, Plutonium, Americium, Curium, Berkelium, "
    "Californium, Einsteinium, Fermium, Mendelevium, Nobelium, Lawrencium, "
    "Rutherfordium, Dubnium, Seaborgium, Bohrium, Hassium, Meitnerium, Darmstadtium, "
    "Roentgenium, Copernicium, Nihonium, Flerovium, Moscovium, Livermorium, "
    "Tennessine, Oganesson"
)

ANIMALS = (
    "Cat, Dog, Horse, Cow, Sheep, Goat, Pig, Chicken, Duck, Goose, Rabbit, Mouse, "
    "Rat, Hamster, Lion, Tiger, Leopard, Jaguar, Cheetah, Wolf, Fox, Bear, Polar bear, "
    "Panda, Giraffe, Zebra, Elephant, Rhinoceros, Hippopotamus, Kangaroo, Koala, "
    "Monkey, Chimpanzee, Gorilla, Orangutan, Dolphin, Whale, Blue whale, Shark, "
    "Octopus, Squid, Jellyfish, Crab, Lobster, Eagle, Hawk, Owl, Penguin, Flamingo, "
    "Parrot, Peacock, Ostrich, Snake, Cobra, Python (genus), Crocodile, Alligator, "
    "Turtle, Tortoise, Frog, Toad, Salamander, Butterfly, Bee, Ant, Spider, Scorpion, "
    "Camel, Llama, Alpaca, Deer, Moose, Bison, Buffalo, Antelope, Gazelle, Squirrel, "
    "Beaver, Otter, Seal, Walrus, Bat, Hedgehog, Armadillo, Sloth, Meerkat, Wombat, "
    "Platypus, Kiwi (bird), Hummingbird, Woodpecker, Salmon, Tuna, Goldfish, "
    "Great white shark, Tyrannosaurus, Velociraptor, Triceratops, Brachiosaurus"
)

EVENTS = (
    "World War I, World War II, Cold War, American Revolutionary War, French Revolution, "
    "Russian Revolution, Industrial Revolution, Renaissance, Age of Enlightenment, "
    "Middle Ages, Ancient Egypt, Ancient Greece, Ancient Rome, Byzantine Empire, "
    "Roman Empire, Ottoman Empire, Mongol Empire, British Empire, Silk Road, "
    "Viking Age, Crusades, Black Death, Protestant Reformation, Age of Discovery, "
    "American Civil War, French and Indian War, Napoleonic Wars, Crimean War, "
    "Meiji Restoration, Russian Civil War, Great Depression, Chinese Civil War, "
    "Korean War, Vietnam War, Space Race, Apollo 11, Fall of the Berlin Wall, "
    "Dissolution of the Soviet Union, September 11 attacks, Cuban Missile Crisis, "
    "American Independence, Magna Carta, Treaty of Versailles, United Nations, "
    "European Union, NATO, Bretton Woods system, Wikipedia, Internet, "
    "History of the telephone, History of television, History of radio"
)

CONCEPTS = (
    "Science, Physics, Chemistry, Biology, Mathematics, Astronomy, Geology, "
    "Meteorology, Oceanography, Ecology, Genetics, Evolution, DNA, Cell (biology), "
    "Photosynthesis, Respiration, Mitosis, Protein, Enzyme, Bacteria, Virus, "
    "Immune system, Human brain, Nervous system, Heart, Blood, Lung, Kidney, Liver, "
    "Skeleton, Muscle, Hormone, Vitamin, Nutrition, Exercise, Sleep, Circadian rhythm, "
    "Disease, Cancer, Diabetes, Malaria, Tuberculosis, Influenza, COVID-19, Vaccine, "
    "Antibiotic, Surgery, Anesthesia, Psychology, Cognitive bias, Memory, Intelligence, "
    "Learning, Philosophy, Ethics, Logic, Metaphysics, Epistemology, Aesthetics, "
    "Political science, Democracy, Republic, Monarchy, Communism, Capitalism, Socialism, "
    "Economics, Inflation, Gross domestic product, Supply and demand, Stock market, "
    "Bank, Interest, Tax, Cryptocurrency, Bitcoin, Blockchain, Money, Trade, "
    "Globalization, Law, Constitution, Human rights, Justice, Education, University, "
    "Language, English language, Grammar, Linguistics, Literature, Poetry, Novel, "
    "Art, Painting, Sculpture, Music, Musical notation, Orchestra, Jazz, Rock music, "
    "Classical music, Dance, Theatre, Film, Cinema, Photography, Architecture, "
    "Mathematics, Algebra, Geometry, Calculus, Trigonometry, Statistics, Probability, "
    "Number theory, Prime number, Pi, Infinity, Set theory, Computer science, "
    "Algorithm, Data structure, Programming language, Python (programming language), "
    "C (programming language), C++, Java (programming language), JavaScript, Rust "
    "(programming language), Operating system, Linux, Microsoft Windows, Android "
    "(operating system), IOS, Software, Computer, Central processing unit, "
    "Graphics processing unit, Random-access memory, Hard disk drive, Internet "
    "protocol suite, World Wide Web, HTTP, Domain Name System, Wi-Fi, Bluetooth, "
    "5G, Smartphone, Tablet computer, Laptop, Artificial intelligence, Machine "
    "learning, Deep learning, Neural network, Large language model, Natural language "
    "processing, Computer vision, Robotics, Automation, Cloud computing, Big data, "
    "Cybersecurity, Encryption, Quantum computing, Quantum mechanics, Theory of "
    "relativity, General relativity, Special relativity, Gravity, Force, Energy, "
    "Matter, Atom, Electron, Proton, Neutron, Molecule, Chemical bond, Periodic table, "
    "Acid, Base (chemistry), Chemical reaction, Thermodynamics, Entropy, Light, "
    "Electromagnetic radiation, Spectrum, Sound, Wave, Electricity, Magnetism, "
    "Electromagnetism, Solar System, Sun, Earth, Moon, Mars, Jupiter, Saturn, "
    "Uranus, Neptune, Venus, Mercury (planet), Pluto, Black hole, Galaxy, Milky Way, "
    "Star, Supernova, Nebula, Universe, Big Bang, Exoplanet, Space exploration, "
    "NASA, International Space Station, Rocket, Satellite, Telescope, Gravity, "
    "Friction, Momentum, Newton's laws of motion, Speed of light, Plate tectonics, "
    "Volcano, Earthquake, Tsunami, Hurricane, Tornado, Climate, Climate change, "
    "Greenhouse effect, Global warming, Ozone layer, Carbon dioxide, Water, Water "
    "cycle, Rain, Snow, Cloud, Wind, Ocean, River, Lake, Desert, Forest, Rainforest, "
    "Mountain, Continent, Africa, Asia, Europe, North America, South America, "
    "Australia (continent), Antarctica, Pacific Ocean, Atlantic Ocean, Indian Ocean, "
    "Arctic Ocean, Southern Ocean, Nile, Amazon River, Himalayas, Mount Everest, "
    "Sahara, Great Barrier Reef, Food, Agriculture, Wheat, Rice, Maize, Potato, "
    "Coffee, Tea, Sugar, Salt, Bread, Cheese, Wine, Beer, Cooking, Recipe, Kitchen, "
    "Sport, Football, Association football, Basketball, Cricket, Tennis, Golf, "
    "Baseball, Rugby, Swimming, Athletics, Olympic Games, FIFA World Cup, Chess, "
    "Go (game), Poker, Video game, Board game, Car, Automobile, Bicycle, Motorcycle, "
    "Train, Airplane, Ship, Submarine, Helicopter, Traffic, Transport, Road, Bridge, "
    "Tunnel, Airport, Port, City, Village, Urban planning, House, Skyscraper, "
    "Pyramid, Great Wall of China, Eiffel Tower, Statue of Liberty, Taj Mahal, "
    "Colosseum, Machu Picchu, Stonehenge, Petra, Christ the Redeemer, Time, Calendar, "
    "Clock, Year, Day, Week, Month, Season, History, Archaeology, Fossil, "
    "Anthropology, Sociology, Geography, Cartography, Map, Flag, Anthem, Currency, "
    "Euro, United States dollar, Japanese yen, Indian rupee, Pound sterling, "
    "Human, Homo sapiens, Civilization, Culture, Religion, Christianity, Islam, "
    "Hinduism, Buddhism, Judaism, Atheism, Prayer, Bible, Quran, Bhagavad Gita, "
    "Meditation, Yoga, Family, Marriage, Child, Friendship, Emotion, Happiness, "
    "Sadness, Fear, Anger, Love, Dream, Consciousness, Death, Birth, Health, "
    "Medicine, Hospital, Doctor, Nurse, Hygiene, Vaccination, First aid, CPR, "
    "Fire, Emergency, Police, Law enforcement, Military, Army, Navy, Air force, "
    "Weapon, Gun, Sword, History of computing, Personal computer, Macintosh, "
    "Microsoft, Apple Inc., Google, Amazon (company), Meta Platforms, Tesla, Inc., "
    "SpaceX, Open-source software, Free software, GitHub, Database, SQL, HTML, "
    "CSS, JSON, XML, API, Server (computing), Client (computing), Network switch, "
    "Router (computing), Data center, Electric battery, Lithium-ion battery, "
    "Solar panel, Wind turbine, Hydroelectricity, Nuclear power, Fossil fuel, "
    "Coal, Petroleum, Natural gas, Renewable energy, Electric vehicle, Hybrid "
    "vehicle, Recycling, Pollution, Plastic, Greenhouse gas, Sustainable "
    "development, Ecosystem, Biodiversity, Endangered species, Extinction, "
    "Dinosaurs, Natural selection, Charles Darwin, Albert Einstein, Isaac Newton, "
    "Galileo Galilei, Marie Curie, Nikola Tesla, Thomas Edison, Alexander Graham "
    "Bell, Wright brothers, Leonardo da Vinci, William Shakespeare, Mozart, "
    "Beethoven, Mahatma Gandhi, Nelson Mandela, Martin Luther King Jr., Abraham "
    "Lincoln, George Washington, Napoleon, Cleopatra, Julius Caesar, Alexander "
    "the Great, Genghis Khan, Confucius, Plato, Aristotle, Socrates, Pythagoras, "
    "Archimedes, Stephen Hawking, Alan Turing, Ada Lovelace, Tim Berners-Lee, "
    "Steve Jobs, Bill Gates, Elon Musk"
)


EXTRAS = (
    "World War I, World War II, Cold War, Soviet Union, Russian Revolution, "
    "French Revolution, American Revolution, American Civil War, Industrial "
    "Revolution, Renaissance, Middle Ages, Ancient Egypt, Ancient Greece, "
    "Ancient Rome, Roman Empire, Byzantine Empire, Ottoman Empire, Mongol "
    "Empire, British Empire, Colonialism, Slavery, The Holocaust, Adolf Hitler, "
    "Joseph Stalin, Winston Churchill, Franklin D. Roosevelt, John F. Kennedy, "
    "Barack Obama, Vladimir Putin, Mao Zedong, Karl Marx, Adam Smith, Martin "
    "Luther, Christopher Columbus, Ferdinand Magellan, Marco Polo, Ibn Battuta, "
    "Ashoka, Akbar, Mughal Empire, British Raj, Indian independence movement, "
    "Bhagat Singh, Subhas Chandra Bose, Jawaharlal Nehru, A. P. J. Abdul Kalam, "
    "Rabindranath Tagore, Swami Vivekananda, Gautama Buddha, Guru Nanak, Jesus, "
    "Muhammad, Moses, Trojan War, Viking, Knight, Castle, Samurai, Pirate, "
    "Gladiator, Silk Road, Age of Discovery, Space Race, Manhattan Project, "
    "Nuclear weapon, Atomic bombings of Hiroshima and Nagasaki, Normandy "
    "landings, Battle of Stalingrad, Attack on Pearl Harbor, Titanic, "
    "Hindenburg disaster, Chernobyl disaster, Fukushima nuclear accident, "
    "Apollo 11, Moon landing, Neil Armstrong, Yuri Gagarin, Sputnik 1, Voyager "
    "program, Hubble Space Telescope, James Webb Space Telescope, Mars rover, "
    "Curiosity (rover), Perseverance (rover), Falcon 9, SpaceX Starship, "
    "Starlink, GPS, Radar, Laser, LED, Transistor, Integrated circuit, "
    "Microprocessor, Moore's law, Computer virus, Malware, Video game console, "
    "PlayStation, Xbox, Nintendo, Minecraft, Fortnite, Super Mario, Pokemon, "
    "Naruto, One Piece, Dragon Ball, Attack on Titan, Demon Slayer, Black "
    "Clover, Anime, Manga, Studio Ghibli, Hayao Miyazaki, Harry Potter, "
    "J. K. Rowling, The Lord of the Rings, Star Wars, Star Trek, Marvel Comics, "
    "DC Comics, Batman, Superman, Spider-Man, Avengers (comics), Disney, "
    "Mickey Mouse, Meow, Cat, Dog, Mona Lisa, The Starry Night, Vincent van "
    "Gogh, Pablo Picasso, The Beatles, Michael Jackson, Bob Marley, Piano, "
    "Guitar, Violin, Singing, Hip hop music, Yoga, Stress (biology), "
    "Anxiety, Depression (mood), Alzheimer's disease, Parkinson's disease, "
    "Autism, Insulin, Penicillin, Pizza, Hamburger, Sushi, Curry, Ice cream, "
    "Pasta, Biryani, Chocolate, Honey, Banana, Apple, Mango, Orange (fruit), "
    "Grape, Strawberry, Tomato, Onion, Garlic, Chili pepper, Ginger, YouTube, "
    "WhatsApp, Instagram, Facebook, TikTok, Reddit, Wikipedia, Google Search, "
    "Gmail, Microsoft Office, Spreadsheet, Adobe Inc., Zoom (software), "
    "Discord, Telegram, Twitter, Jeff Bezos, Mark Zuckerberg, Sundar Pichai, "
    "Sam Altman, ChatGPT, OpenAI, AlphaGo, Dark matter, Dark energy, Solar "
    "eclipse, Aurora, Rainbow, Lightning, Lithium, Helium, Hydrogen, Oxygen, "
    "Carbon, Nitrogen, Gold, Silver, Iron, Copper, Diamond, Greenhouse gas "
    "emissions, Extinction event, Woolly mammoth, Dinosaur, Tyrannosaurus, "
    "Blue whale, Elephant, Lion, Tiger, Panda, Penguin, Eagle, Shark, "
    "Butterfly, Bee, Ant, Spider, Snake, Crocodile, Dolphin, Whale, Horse, "
    "Cow, Sheep, Goat, Chicken, Camel, Kangaroo, Koala, Monkey, Gorilla, "
    "Chimpanzee, Octopus, Jellyfish, Coral, Mushroom, Tree, Oak, Bamboo, "
    "Rose, Lotus, Tulip, Sunflower, Cactus, Venus flytrap"
)


def build_topic_list():
    topics = []
    seen = set()
    for group in (EXTRAS, CONCEPTS, COUNTRIES, ELEMENTS, ANIMALS, EVENTS):
        for t in group.split(","):
            t = t.strip()
            if t and t.lower() not in seen:
                seen.add(t.lower())
                topics.append(t)
    return topics


def fetch_extracts(titles):
    url = ("https://en.wikipedia.org/w/api.php?action=query&format=json"
           "&prop=extracts&explaintext=1&redirects=1&exlimit=20&titles="
           + quote("|".join(titles)))
    raw, r = websearch.http_get(url, timeout=40, max_bytes=9000000)
    data = json.loads(raw.decode("utf-8", "ignore"))
    out = {}
    for page in (data.get("query", {}).get("pages", {}) or {}).values():
        title = page.get("title")
        ext = page.get("extract")
        if title and ext and len(ext) > 200:
            out[title] = ext
    return out


def fetch_one(title, retries=3):
    """Fetch one article's full plain-text extract (exlimit=1 per request is
    the API maximum for whole-article extracts)."""
    url = ("https://en.wikipedia.org/w/api.php?action=query&format=json"
           "&prop=extracts&explaintext=1&redirects=1&exlimit=1&titles="
           + quote(title))
    last = None
    for attempt in range(retries):
        try:
            raw, r = websearch.http_get(url, timeout=40, max_bytes=5000000)
            data = json.loads(raw.decode("utf-8", "ignore"))
            for page in (data.get("query", {}).get("pages", {}) or {}).values():
                ext = page.get("extract")
                if ext and len(ext) > 200:
                    return page.get("title") or title, ext
            return title, None
        except Exception as e:
            last = e
            time.sleep(30.0 if "429" in repr(e) else 3.0)
    raise last


def fetch_summary(title):
    """Fetch the intro summary of one article (fast, small)."""
    url = ("https://en.wikipedia.org/api/rest_v1/page/summary/"
           + quote(title.replace(" ", "_")))
    raw, r = websearch.http_get(url, timeout=30, max_bytes=300000)
    data = json.loads(raw.decode("utf-8", "ignore"))
    ext = data.get("extract")
    if ext and len(ext) > 120:
        return data.get("title") or title, ext
    return title, None


def _missing_titles(mem, done):
    try:
        cur = mem.conn.execute("SELECT url FROM docs WHERE url LIKE 'wiki://%'")
        stored = set(r[0][len("wiki://"):].replace("_", " ") for r in cur.fetchall())
    except Exception:
        return []
    return [t for t in sorted(done) if t not in stored]


def _run_fetch(fetcher, titles, mem, log, time_budget, workers, gap,
               chars_per_article, done, stats, saved_every=10):
    t0 = time.time()
    q = queue.Queue()
    for t in titles:
        q.put(t)
    results = queue.Queue()

    def worker():
        while time.time() - t0 <= time_budget:
            try:
                title = q.get_nowait()
            except queue.Empty:
                return
            websearch._throttle(gap)
            try:
                t, ext = fetcher(title)
            except Exception as e:
                results.put((title, None, repr(e)))
                continue
            results.put((title, ext, None))

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(workers)]
    for th in threads:
        th.start()
    pending = len(titles)
    while pending > 0:
        try:
            title, ext, err = results.get(timeout=1.0)
        except queue.Empty:
            if not any(th.is_alive() for th in threads):
                break
            continue
        pending -= 1
        if err:
            log("fetch failed: %s (%s)" % (err, title))
            continue
        if ext:
            ids = mem.add_passages("wiki://" + title.replace(" ", "_"), title,
                                   ext[:chars_per_article], source="knowledge",
                                   topic=title.lower())
            stats["articles"] += 1
            stats["passages"] += len(ids)
        done.add(title)
        if len(done) % saved_every == 0:
            mem.kv_set("knowledge_seeded_titles", sorted(done))
            log("knowledge pack: %d fetched, %d passages, %.0fs elapsed"
                % (stats["articles"], stats["passages"], time.time() - t0))
    for th in threads:
        th.join(timeout=5)
    return stats


def fetch_intro_batch(titles, retries=3):
    """Fetch intro extracts for up to 20 titles in ONE request (fast coverage)."""
    url = ("https://en.wikipedia.org/w/api.php?action=query&format=json"
           "&prop=extracts&explaintext=1&exintro=1&redirects=1&exlimit=20&titles="
           + quote("|".join(titles)))
    last = None
    for attempt in range(retries):
        try:
            raw, r = websearch.http_get(url, timeout=40, max_bytes=3000000)
            data = json.loads(raw.decode("utf-8", "ignore"))
            out = {}
            for page in (data.get("query", {}).get("pages", {}) or {}).values():
                title = page.get("title")
                ext = page.get("extract")
                if title and ext and len(ext) > 120:
                    out[title] = ext
            return out
        except Exception as e:
            last = e
            time.sleep(20.0 if "429" in repr(e) else 3.0)
    raise last


def _stored_chars(mem):
    out = {}
    try:
        cur = mem.conn.execute(
            "SELECT url, SUM(LENGTH(passage)) s FROM docs WHERE url LIKE 'wiki://%' "
            "GROUP BY url")
        for url, s in cur.fetchall():
            out[url[len("wiki://"):].replace("_", " ")] = s or 0
    except Exception:
        pass
    return out


def seed_knowledge(mem, log=print, max_articles=1200, chars_per_article=12000,
                   time_budget=2400, workers=2, gap=2.0):
    todos = build_topic_list()[:max_articles]
    done = set(mem.kv_get("knowledge_seeded_titles", []) or [])
    deep = set(mem.kv_get("knowledge_deep_titles", []) or [])
    stored = _stored_chars(mem)
    deep |= set(t for t, n in stored.items() if n >= 6000)
    stats = {"articles": 0, "passages": 0, "intros": 0, "recovered": 0, "deep": 0}
    t0 = time.time()

    # phase 1: intro coverage for every remaining topic (20 per request)
    remaining = [t for t in todos if t not in done]
    log("knowledge pack: %d topics, %d done, %d to cover"
        % (len(todos), len(done), len(remaining)))
    for i in range(0, len(remaining), 20):
        if time.time() - t0 > time_budget * 0.2:
            log("intro phase time budget reached")
            break
        batch = remaining[i:i + 20]
        websearch._throttle(1.3)
        try:
            intros = fetch_intro_batch(batch)
        except Exception as e:
            log("intro batch failed: %r" % e)
            continue
        for title, ext in intros.items():
            ids = mem.add_passages("wiki://" + title.replace(" ", "_"), title,
                                   ext[:3000], source="knowledge",
                                   topic=title.lower())
            stats["intros"] += 1
            stats["passages"] += len(ids)
        for t in batch:
            done.add(t)
        mem.kv_set("knowledge_seeded_titles", sorted(done))
        if i % 200 == 0 and i:
            log("knowledge pack: %d intros, %.0fs elapsed"
                % (stats["intros"], time.time() - t0))

    # phase 2: recover topics marked done but with (almost) no stored content
    for _pass in range(2):
        stored = _stored_chars(mem)
        missing = [t for t in todos if stored.get(t, 0) < 400]
        if not missing:
            break
        log("recovering %d topics with no stored content (pass %d)"
            % (len(missing), _pass + 1))
        for i in range(0, len(missing), 20):
            if time.time() - t0 > time_budget * 0.4:
                log("recovery phase time budget reached")
                break
            batch = missing[i:i + 20]
            websearch._throttle(1.3)
            try:
                intros = fetch_intro_batch(batch)
            except Exception as e:
                log("recovery batch failed: %r" % e)
                time.sleep(15.0)
                continue
            for title, ext in intros.items():
                ids = mem.add_passages("wiki://" + title.replace(" ", "_"), title,
                                       ext[:3000], source="knowledge",
                                       topic=title.lower())
                stats["recovered"] += 1
                stats["passages"] += len(ids)

    # phase 3: depth - full articles for topics that only have intros
    candidates = [t for t in todos if t not in deep]
    log("depth phase: %d topics to deepen" % len(candidates))
    for title in candidates:
        if time.time() - t0 > time_budget:
            log("depth phase time budget reached")
            break
        websearch._throttle(gap)
        try:
            t, ext = fetch_one(title)
        except Exception as e:
            log("deep fetch failed: %r (%s)" % (e, title))
            continue
        if ext:
            ids = mem.add_passages("wiki://" + t.replace(" ", "_"), t,
                                   ext[:chars_per_article], source="knowledge",
                                   topic=t.lower())
            stats["deep"] += 1
            stats["articles"] += 1
            stats["passages"] += len(ids)
            deep.add(t)
            if stats["deep"] % 10 == 0:
                mem.kv_set("knowledge_deep_titles", sorted(deep))
                log("knowledge pack: %d deepened, %d passages, %.0fs elapsed"
                    % (stats["deep"], stats["passages"], time.time() - t0))
    mem.kv_set("knowledge_seeded_titles", sorted(done))
    mem.kv_set("knowledge_deep_titles", sorted(deep))
    stats["seconds"] = round(time.time() - t0, 1)
    log("knowledge pack done: %s" % stats)
    return stats
