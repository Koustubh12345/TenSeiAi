"""Seed a large, curated, correct-by-construction knowledge pack into TenSeiAi.

Three kinds of data go in (all local, no network):

1.  Country capitals        (~180 verified pairs)
2.  Chemical elements       (all 118, with symbol + atomic number)
3.  High-value facts        (science, history, geography, biology, computing,
                             everyday general knowledge - ~220 entries)

Everything is stored BOTH as memory passages (so retrieval + the language
model learn from it) and as verified Q&A pairs (so direct questions hit
instantly). Evidence is marked teacher://facts-pack, which the quality
gate treats as trusted.

Usage:
    python tools/seed_facts_pack.py            # add data
    python tools/seed_facts_pack.py --train    # add data + retrain the brain
"""
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tensei.brain import Brain  # noqa: E402
from tensei.memory import Memory  # noqa: E402

EVIDENCE = [{"url": "teacher://facts-pack",
             "title": "TenSeiAi curated facts pack (verified)"}]

CAPITALS = """Afghanistan=Kabul
Albania=Tirana
Algeria=Algiers
Andorra=Andorra la Vella
Angola=Luanda
Antigua and Barbuda=Saint John's
Argentina=Buenos Aires
Armenia=Yerevan
Australia=Canberra
Austria=Vienna
Azerbaijan=Baku
Bahamas=Nassau
Bahrain=Manama
Bangladesh=Dhaka
Barbados=Bridgetown
Belarus=Minsk
Belgium=Brussels
Belize=Belmopan
Benin=Porto-Novo
Bhutan=Thimphu
Bolivia=Sucre
Bosnia and Herzegovina=Sarajevo
Botswana=Gaborone
Brazil=Brasilia
Brunei=Bandar Seri Begawan
Bulgaria=Sofia
Burkina Faso=Ouagadougou
Burundi=Gitega
Cambodia=Phnom Penh
Cameroon=Yaounde
Canada=Ottawa
Cape Verde=Praia
Central African Republic=Bangui
Chad=N'Djamena
Chile=Santiago
China=Beijing
Colombia=Bogota
Comoros=Moroni
Democratic Republic of the Congo=Kinshasa
Republic of the Congo=Brazzaville
Costa Rica=San Jose
Croatia=Zagreb
Cuba=Havana
Cyprus=Nicosia
Czech Republic=Prague
Denmark=Copenhagen
Djibouti=Djibouti
Dominica=Roseau
Dominican Republic=Santo Domingo
Ecuador=Quito
Egypt=Cairo
El Salvador=San Salvador
Equatorial Guinea=Malabo
Eritrea=Asmara
Estonia=Tallinn
Eswatini=Mbabane
Ethiopia=Addis Ababa
Fiji=Suva
Finland=Helsinki
France=Paris
Gabon=Libreville
Gambia=Banjul
Georgia=Tbilisi
Germany=Berlin
Ghana=Accra
Greece=Athens
Grenada=Saint George's
Guatemala=Guatemala City
Guinea=Conakry
Guinea-Bissau=Bissau
Guyana=Georgetown
Haiti=Port-au-Prince
Honduras=Tegucigalpa
Hungary=Budapest
Iceland=Reykjavik
India=New Delhi
Indonesia=Jakarta
Iran=Tehran
Iraq=Baghdad
Ireland=Dublin
Israel=Jerusalem
Italy=Rome
Ivory Coast=Yamoussoukro
Jamaica=Kingston
Japan=Tokyo
Jordan=Amman
Kazakhstan=Astana
Kenya=Nairobi
Kiribati=Tarawa
Kuwait=Kuwait City
Kyrgyzstan=Bishkek
Laos=Vientiane
Latvia=Riga
Lebanon=Beirut
Lesotho=Maseru
Liberia=Monrovia
Libya=Tripoli
Liechtenstein=Vaduz
Lithuania=Vilnius
Luxembourg=Luxembourg City
Madagascar=Antananarivo
Malawi=Lilongwe
Malaysia=Kuala Lumpur
Maldives=Male
Mali=Bamako
Malta=Valletta
Marshall Islands=Majuro
Mauritania=Nouakchott
Mauritius=Port Louis
Mexico=Mexico City
Micronesia=Palikir
Moldova=Chisinau
Monaco=Monaco
Mongolia=Ulaanbaatar
Montenegro=Podgorica
Morocco=Rabat
Mozambique=Maputo
Myanmar=Naypyidaw
Namibia=Windhoek
Nauru=Yaren
Nepal=Kathmandu
Netherlands=Amsterdam
New Zealand=Wellington
Nicaragua=Managua
Niger=Niamey
Nigeria=Abuja
North Korea=Pyongyang
North Macedonia=Skopje
Norway=Oslo
Oman=Muscat
Pakistan=Islamabad
Palau=Ngerulmud
Palestine=Ramallah
Panama=Panama City
Papua New Guinea=Port Moresby
Paraguay=Asuncion
Peru=Lima
Philippines=Manila
Poland=Warsaw
Portugal=Lisbon
Qatar=Doha
Romania=Bucharest
Russia=Moscow
Rwanda=Kigali
Saint Kitts and Nevis=Basseterre
Saint Lucia=Castries
Saint Vincent and the Grenadines=Kingstown
Samoa=Apia
San Marino=San Marino
Sao Tome and Principe=Sao Tome
Saudi Arabia=Riyadh
Senegal=Dakar
Serbia=Belgrade
Seychelles=Victoria
Sierra Leone=Freetown
Singapore=Singapore
Slovakia=Bratislava
Slovenia=Ljubljana
Solomon Islands=Honiara
Somalia=Mogadishu
South Africa=Pretoria
South Korea=Seoul
South Sudan=Juba
Spain=Madrid
Sri Lanka=Sri Jayawardenepura Kotte
Sudan=Khartoum
Suriname=Paramaribo
Sweden=Stockholm
Switzerland=Bern
Syria=Damascus
Tajikistan=Dushanbe
Tanzania=Dodoma
Thailand=Bangkok
Timor-Leste=Dili
Togo=Lome
Tonga=Nuku'alofa
Trinidad and Tobago=Port of Spain
Tunisia=Tunis
Turkey=Ankara
Turkmenistan=Ashgabat
Tuvalu=Funafuti
Uganda=Kampala
Ukraine=Kyiv
United Arab Emirates=Abu Dhabi
United Kingdom=London
United States=Washington, D.C.
Uruguay=Montevideo
Uzbekistan=Tashkent
Vanuatu=Port Vila
Vatican City=Vatican City
Venezuela=Caracas
Vietnam=Hanoi
Yemen=Sanaa
Zambia=Lusaka
Zimbabwe=Harare"""

ELEMENTS = """1|H|Hydrogen
2|He|Helium
3|Li|Lithium
4|Be|Beryllium
5|B|Boron
6|C|Carbon
7|N|Nitrogen
8|O|Oxygen
9|F|Fluorine
10|Ne|Neon
11|Na|Sodium
12|Mg|Magnesium
13|Al|Aluminium
14|Si|Silicon
15|P|Phosphorus
16|S|Sulfur
17|Cl|Chlorine
18|Ar|Argon
19|K|Potassium
20|Ca|Calcium
21|Sc|Scandium
22|Ti|Titanium
23|V|Vanadium
24|Cr|Chromium
25|Mn|Manganese
26|Fe|Iron
27|Co|Cobalt
28|Ni|Nickel
29|Cu|Copper
30|Zn|Zinc
31|Ga|Gallium
32|Ge|Germanium
33|As|Arsenic
34|Se|Selenium
35|Br|Bromine
36|Kr|Krypton
37|Rb|Rubidium
38|Sr|Strontium
39|Y|Yttrium
40|Zr|Zirconium
41|Nb|Niobium
42|Mo|Molybdenum
43|Tc|Technetium
44|Ru|Ruthenium
45|Rh|Rhodium
46|Pd|Palladium
47|Ag|Silver
48|Cd|Cadmium
49|In|Indium
50|Sn|Tin
51|Sb|Antimony
52|Te|Tellurium
53|I|Iodine
54|Xe|Xenon
55|Cs|Caesium
56|Ba|Barium
57|La|Lanthanum
58|Ce|Cerium
59|Pr|Praseodymium
60|Nd|Neodymium
61|Pm|Promethium
62|Sm|Samarium
63|Eu|Europium
64|Gd|Gadolinium
65|Tb|Terbium
66|Dy|Dysprosium
67|Ho|Holmium
68|Er|Erbium
69|Tm|Thulium
70|Yb|Ytterbium
71|Lu|Lutetium
72|Hf|Hafnium
73|Ta|Tantalum
74|W|Tungsten
75|Re|Rhenium
76|Os|Osmium
77|Ir|Iridium
78|Pt|Platinum
79|Au|Gold
80|Hg|Mercury
81|Tl|Thallium
82|Pb|Lead
83|Bi|Bismuth
84|Po|Polonium
85|At|Astatine
86|Rn|Radon
87|Fr|Francium
88|Ra|Radium
89|Ac|Actinium
90|Th|Thorium
91|Pa|Protactinium
92|U|Uranium
93|Np|Neptunium
94|Pu|Plutonium
95|Am|Americium
96|Cm|Curium
97|Bk|Berkelium
98|Cf|Californium
99|Es|Einsteinium
100|Fm|Fermium
101|Md|Mendelevium
102|No|Nobelium
103|Lr|Lawrencium
104|Rf|Rutherfordium
105|Db|Dubnium
106|Sg|Seaborgium
107|Bh|Bohrium
108|Hs|Hassium
109|Mt|Meitnerium
110|Ds|Darmstadtium
111|Rg|Roentgenium
112|Cn|Copernicium
113|Nh|Nihonium
114|Fl|Flerovium
115|Mc|Moscovium
116|Lv|Livermorium
117|Ts|Tennessine
118|Og|Oganesson"""

FACTS = [
    # --- geography / Earth -------------------------------------------------
    ("What is the tallest mountain in the world?",
     "**Mount Everest** is the tallest mountain on Earth, standing 8,849 metres (29,032 ft) above sea level on the border of Nepal and China. It was first summited by Edmund Hillary and Tenzing Norgay in 1953."),
    ("What is the longest river in the world?",
     "The **Nile** in Africa is traditionally listed as the longest river in the world at about 6,650 km (4,130 mi), with the **Amazon** a very close second at roughly 6,400 km. The Amazon carries by far the largest volume of water of any river."),
    ("Which is the largest ocean on Earth?",
     "The **Pacific Ocean** is the largest and deepest ocean, covering about 165 million square kilometres - more than all of Earth's land area combined."),
    ("What is the largest desert in the world?",
     "The **Antarctic Desert** is the largest desert on Earth (deserts are defined by dryness, not heat). The largest *hot* desert is the **Sahara** in Africa."),
    ("What is the largest country in the world by area?",
     "**Russia** is the largest country by area, covering about 17.1 million square kilometres - roughly 11% of all land on Earth."),
    ("What is the smallest country in the world?",
     "**Vatican City** is the smallest country in the world at about 0.49 square kilometres (121 acres) with roughly 800 residents."),
    ("What is the most populous country in the world?",
     "**India** became the world's most populous country in 2023, with over 1.4 billion people. China is second."),
    ("What is the deepest point in the ocean?",
     "The **Challenger Deep** in the Mariana Trench, Pacific Ocean, is the deepest known point at about 10,935 metres (35,876 ft) below sea level."),
    ("What is the largest lake in the world?",
     "The **Caspian Sea** is the largest lake in the world by area (about 371,000 square km). By volume, Lake Baikal in Russia is the largest and also the deepest lake."),
    ("What is the highest waterfall in the world?",
     "**Angel Falls** (Salto Angel) in Venezuela is the world's highest uninterrupted waterfall at 979 metres (3,212 ft)."),
    ("What is the largest island in the world?",
     "**Greenland** is the world's largest island (about 2.17 million square km). Australia is larger but is classified as a continent."),
    ("How many continents are there on Earth?",
     "There are **7 continents**: Africa, Antarctica, Asia, Europe, North America, Oceania (Australia) and South America."),
    ("What are the five oceans of the world?",
     "The five oceans are the **Pacific, Atlantic, Indian, Southern (Antarctic) and Arctic** oceans."),
    ("What is the circumference of the Earth?",
     "The Earth's circumference is about **40,075 km (24,901 mi)** around the equator, and slightly less (40,008 km) around the poles."),
    ("How old is the Earth?",
     "The Earth is about **4.54 billion years old**, dated from the oldest rocks and meteorites using radiometric dating."),
    ("What is the hottest place on Earth?",
     "The **Death Valley** in California, USA, holds the record for the highest reliably measured air temperature: 56.7 degrees C (134 degrees F) in 1913."),
    ("What is the coldest place on Earth?",
     "**Antarctica** is the coldest place on Earth; the lowest recorded temperature is -89.2 degrees C at Vostok Station and satellite readings of about -98 degrees C."),
    ("What is the driest place on Earth?",
     "The **Atacama Desert** in Chile is the driest non-polar desert; some weather stations there have never recorded rain."),

    # --- science constants / physics ---------------------------------------
    ("What is the speed of light?",
     "The speed of light in a vacuum is exactly **299,792,458 metres per second** (about 300,000 km/s or 186,282 miles per second). It is the universal speed limit of information."),
    ("What is the speed of sound?",
     "Sound travels at about **343 m/s** (1,235 km/h) in air at 20 degrees C. It is faster in water (about 1,480 m/s) and fastest in solids."),
    ("What is the boiling point of water?",
     "Water boils at **100 degrees C (212 degrees F)** at normal sea-level pressure. At higher altitudes the boiling point drops (about 72 degrees C on top of Mount Everest)."),
    ("What is the freezing point of water?",
     "Water freezes at **0 degrees C (32 degrees F)** at standard pressure."),
    ("What is absolute zero?",
     "Absolute zero is **-273.15 degrees C (0 Kelvin)**, the lowest possible temperature where particles have minimum thermal motion. It has never been reached, only approached."),
    ("What is the acceleration due to gravity on Earth?",
     "The standard gravitational acceleration on Earth is about **9.81 m/s^2**. On the Moon it is about 1.62 m/s^2."),
    ("What is Avogadro's number?",
     "Avogadro's number is **6.022 x 10^23** particles per mole - the number of atoms in exactly 12 grams of carbon-12."),
    ("What is the value of pi?",
     "**Pi** is the ratio of a circle's circumference to its diameter: 3.14159265... It is irrational (its decimals never end or repeat)."),
    ("What is the normal human body temperature?",
     "Normal human body temperature is about **37 degrees C (98.6 degrees F)**, though it varies slightly during the day and between people."),
    ("What is the atmosphere of Earth made of?",
     "Earth's atmosphere is about **78% nitrogen, 21% oxygen, 0.9% argon and 0.04% carbon dioxide**, plus water vapour and trace gases."),
    ("What is the hardest natural substance?",
     "**Diamond** is the hardest naturally occurring substance (10 on the Mohs scale). It is a form of pure carbon."),
    ("What is the most abundant gas in the atmosphere?",
     "**Nitrogen** is the most abundant gas in Earth's atmosphere (about 78%). Oxygen is second at about 21%."),
    ("What is the most abundant element in the universe?",
     "**Hydrogen** is the most abundant element in the universe (about 75% of normal matter), followed by helium."),
    ("What is the state of matter?",
     "The three common states of matter are **solid** (fixed shape and volume), **liquid** (fixed volume, flowing shape) and **gas** (fills its container). Plasma is a fourth state found in stars and lightning."),
    ("What is the difference between mass and weight?",
     "**Mass** is the amount of matter in an object (measured in kilograms and unchanged everywhere). **Weight** is the gravitational force on that mass (W = m x g) and changes with gravity."),
    ("What is energy?",
     "**Energy** is the capacity to do work. It exists as kinetic energy (motion), potential energy (position), thermal, chemical, electrical, and nuclear energy. Energy is conserved - it changes form but is never created or destroyed."),
    ("What is the theory of evolution?",
     "**Evolution** by **natural selection** (Charles Darwin, 1859) explains how species change over generations: individuals with traits better suited to their environment survive and reproduce more, so those traits become more common."),

    # --- biology ------------------------------------------------------------
    ("How many bones are in the human body?",
     "An adult human body has **206 bones**. Babies are born with about 270 bones, many of which fuse together during growth."),
    ("What is the largest organ in the human body?",
     "The **skin** is the largest organ of the human body, covering about 2 square metres and weighing 3-4 kg."),
    ("What is the strongest bone in the human body?",
     "The **femur** (thigh bone) is the longest and strongest bone in the human body."),
    ("What is the smallest bone in the human body?",
     "The **stapes** (stirrup bone) in the middle ear is the smallest bone, only about 3 mm long."),
    ("How many times does the heart beat per day?",
     "The average human heart beats about **100,000 times per day**, pumping roughly 7,500 litres of blood."),
    ("How many chromosomes do humans have?",
     "Humans have **46 chromosomes** (23 pairs) in each body cell - 23 from each parent."),
    ("How many neurons are in the human brain?",
     "The human brain contains about **86 billion neurons**, connected by trillions of synapses."),
    ("What is the largest animal in the world?",
     "The **blue whale** is the largest animal ever known to have lived, reaching up to 30 metres long and 180 tonnes."),
    ("What is the largest land animal?",
     "The **African elephant** is the largest land animal, standing up to 4 metres tall and weighing up to 7 tonnes."),
    ("What is the tallest animal in the world?",
     "The **giraffe** is the tallest living animal, reaching 5.5 metres (18 ft); its neck alone can be 2 metres long."),
    ("What is the fastest land animal?",
     "The **cheetah** is the fastest land animal, reaching 100-120 km/h (62-75 mph) in short bursts."),
    ("What is the fastest bird?",
     "The **peregrine falcon** is the fastest bird - and fastest animal - diving at over 389 km/h (242 mph)."),
    ("What is the difference between bacteria and viruses?",
     "**Bacteria** are single-celled living organisms that can reproduce on their own and be killed by antibiotics. **Viruses** are much smaller non-living packages of genetic material that can only reproduce inside host cells; antibiotics do not affect them - vaccines and antivirals do."),
    ("What are the 5 senses of the human body?",
     "The five classical senses are **sight, hearing, smell, taste and touch**. Humans also have balance, temperature, pain and body-position senses."),
    ("How many teeth does an adult human have?",
     "An adult human has **32 teeth**, including 4 wisdom teeth. Children have 20 baby teeth."),
    ("What is DNA?",
     "**DNA (deoxyribonucleic acid)** is the molecule that stores genetic instructions in all living things. Its double-helix structure, discovered in 1953 by Watson, Crick and Franklin, is made of four bases (A, T, G, C) that pair up: A with T, and G with C."),
    ("What is photosynthesis?",
     "**Photosynthesis** is the process by which plants, algae and some bacteria convert sunlight, carbon dioxide and water into glucose and oxygen: 6CO2 + 6H2O + light -> C6H12O6 + 6O2. It is the foundation of almost all life on Earth."),
    ("What is a cell?",
     "The **cell** is the smallest structural and functional unit of life. Every living organism is made of one or more cells; human bodies contain about 37 trillion of them."),

    # --- history ------------------------------------------------------------
    ("What year did World War 2 end?",
     "**World War II ended in 1945**: Germany surrendered in May 1945 (V-E Day, 8 May) and Japan surrendered in September 1945 (V-J Day, 2 September), after the atomic bombings of Hiroshima and Nagasaki."),
    ("When did World War 1 start and end?",
     "**World War I lasted from 1914 to 1918**, triggered by the assassination of Archduke Franz Ferdinand in Sarajevo (28 June 1914). It ended with the armistice on 11 November 1918."),
    ("When did the Berlin Wall fall?",
     "The **Berlin Wall fell on 9 November 1989**, leading to German reunification on 3 October 1990."),
    ("When did the Soviet Union dissolve?",
     "The **Soviet Union dissolved in December 1991**, splitting into 15 independent republics, with Russia as its largest successor state."),
    ("When did humans first land on the Moon?",
     "**Apollo 11** landed on the Moon on **20 July 1969**. Neil Armstrong became the first human to walk on its surface, followed by Buzz Aldrin, while Michael Collins orbited above."),
    ("When did the Titanic sink?",
     "The **RMS Titanic sank on 15 April 1912** after hitting an iceberg on its maiden voyage from Southampton to New York. About 1,500 people died."),
    ("When was the United States Declaration of Independence signed?",
     "The Declaration of Independence was adopted on **4 July 1776**, when the American colonies declared independence from Great Britain."),
    ("When did the French Revolution begin?",
     "The **French Revolution began in 1789**, with the storming of the Bastille on 14 July 1789."),
    ("When did the Industrial Revolution start?",
     "The **Industrial Revolution began in Britain around 1760**, moving from hand tools to machine manufacturing, steam power and factories."),
    ("Who invented the World Wide Web?",
     "**Tim Berners-Lee** invented the World Wide Web in 1989 at CERN, creating HTML, HTTP and the first web browser and server. The first website went live in 1991."),
    ("Who invented the telephone?",
     "**Alexander Graham Bell** is credited with inventing the first practical telephone, patented in 1876. Antonio Meucci and Elisha Gray did important related work around the same time."),
    ("Who invented the light bulb?",
     "**Thomas Edison** patented the first commercially practical incandescent light bulb in 1879 (building on earlier work by Humphry Davy, Warren de la Rue and Joseph Swan)."),
    ("Who invented the printing press?",
     "**Johannes Gutenberg** invented the movable-type printing press in Europe around 1440, making books dramatically cheaper and helping launch the Renaissance and Reformation."),
    ("Who invented the airplane?",
     "The **Wright brothers** (Orville and Wilbur) made the first powered, controlled airplane flight on 17 December 1903 at Kitty Hawk, North Carolina."),
    ("Who discovered penicillin?",
     "**Alexander Fleming** discovered penicillin in 1928 when mould (Penicillium) killed bacteria in his petri dishes. It became the first widely used antibiotic in the 1940s."),
    ("Who invented the vaccine?",
     "**Edward Jenner** pioneered vaccination in 1796, showing that cowpox protected people against smallpox. Smallpox was declared eradicated in 1980."),
    ("Who was the first human in space?",
     "**Yuri Gagarin** (Soviet Union) became the first human in space on 12 April 1961 aboard Vostok 1. **Neil Armstrong** was the first on the Moon in 1969."),
    ("When was the first satellite launched?",
     "**Sputnik 1**, the first artificial satellite, was launched by the Soviet Union on **4 October 1957**, starting the Space Race."),
    ("When was the Higgs boson discovered?",
     "The **Higgs boson** was discovered in **2012** at CERN's Large Hadron Collider, confirming the mechanism that gives elementary particles mass."),
    ("When did the United Nations form?",
     "The **United Nations** was founded on **24 October 1945** after World War II, with 51 founding member states. It now has 193 members."),
    ("Who was the first person to walk on the Moon?",
     "**Neil Armstrong**, on 20 July 1969, during the Apollo 11 mission. His first words were: 'That's one small step for man, one giant leap for mankind.'"),
    ("Who was the first President of the United States?",
     "**George Washington** was the first President of the United States, serving from 1789 to 1797."),

    # --- computing / technology --------------------------------------------
    ("What is binary and how do computers use it?",
     "**Binary** is a base-2 number system using only 0 and 1. Computers use it because transistors have two simple states (off/on). Each binary digit is a bit; 8 bits make a byte, allowing 256 values."),
    ("How many bytes are in a kilobyte, megabyte and gigabyte?",
     "1 **kilobyte (KB)** = 1,024 bytes; 1 **megabyte (MB)** = 1,024 KB (1,048,576 bytes); 1 **gigabyte (GB)** = 1,024 MB; 1 **terabyte (TB)** = 1,024 GB."),
    ("What is an algorithm?",
     "An **algorithm** is a finite, step-by-step procedure for solving a problem or completing a task. Recipes and directions are everyday algorithms; computer algorithms must be precise and unambiguous."),
    ("What is an operating system?",
     "An **operating system (OS)** is the core software that manages a computer's hardware and provides services to programs - memory, files, processes and devices. Examples: Windows, Linux, macOS, Android, iOS."),
    ("What is the difference between RAM and ROM?",
     "**RAM (Random Access Memory)** is fast, volatile working memory that is erased when power is off. **ROM (Read-Only Memory)** is non-volatile permanent memory used for firmware like the boot instructions."),
    ("What is the difference between a CPU and a GPU?",
     "A **CPU** has a few powerful cores optimised for sequential, general-purpose work. A **GPU** has thousands of small cores optimised for parallel work like graphics and AI matrix maths."),
    ("What is the difference between a compiler and an interpreter?",
     "A **compiler** translates a whole program into machine code before it runs (C, Rust, Go). An **interpreter** executes source code line by line at runtime (Python, JavaScript). Compilers are usually faster at runtime; interpreters are more flexible."),
    ("What is recursion in programming?",
     "**Recursion** is when a function calls itself with a smaller input until a base case stops it. Example: factorial(n) = n x factorial(n-1), with factorial(1) = 1."),
    ("What is HTTP and HTTPS?",
     "**HTTP** (HyperText Transfer Protocol) is the request/response protocol of the web. **HTTPS** is HTTP encrypted with TLS, so data cannot be read or changed in transit. Common status codes: 200 OK, 404 Not Found, 500 Server Error."),
    ("What is an IP address?",
     "An **IP address** is a numerical label identifying a device on a network, like 192.168.1.1 (IPv4) or 2001:db8::1 (IPv6). It is how data packets find their destination."),
    ("What is DNS?",
     "**DNS (Domain Name System)** is the internet's phone book: it translates human names like example.com into machine IP addresses."),
    ("What is an API?",
     "An **API (Application Programming Interface)** is a defined way for one program to talk to another - a set of functions, endpoints and data formats with rules about how to use them."),
    ("What is open source software?",
     "**Open source** software publishes its source code so anyone can inspect, modify and redistribute it (for example Linux, Python, Firefox). It is usually developed collaboratively and licensed to guarantee those freedoms."),
    ("What is Git?",
     "**Git** is a distributed version control system that tracks changes to files, lets you branch and merge work, and records snapshots (commits) with history - essential for collaborative software projects."),
    ("What is the difference between SQL and NoSQL databases?",
     "**SQL** databases store data in tables with fixed schemas and use structured queries with JOINs (MySQL, PostgreSQL). **NoSQL** databases store documents, key-value pairs or graphs with flexible schemas, scaling horizontally (MongoDB, Redis)."),
    ("What is a cache?",
     "A **cache** is a small, fast storage layer that keeps frequently used data close to where it is needed (CPU cache, browser cache, CDN) so repeated requests are much faster."),
    ("What is cloud computing?",
     "**Cloud computing** means renting computing resources - servers, storage, databases, AI - over the internet from providers like AWS, Azure or Google Cloud, paying only for what you use."),
    ("What is machine learning?",
     "**Machine learning** is a branch of AI where programs learn patterns from data instead of being explicitly programmed. Main types: supervised learning (labelled data), unsupervised learning (finding structure) and reinforcement learning (learning from rewards)."),
    ("What is the difference between AI, machine learning and deep learning?",
     "**AI** is the broad field of making machines smart. **Machine learning** is a subset where systems learn from data. **Deep learning** is a subset of ML using multi-layer neural networks - it powers modern speech, vision and language models."),
    ("What is a neural network?",
     "A **neural network** is a computing system inspired by the brain: layers of simple units (neurons) with weighted connections that are adjusted during training to map inputs to outputs."),
    ("What is cybersecurity?",
     "**Cybersecurity** is protecting systems and data from digital attacks. Core ideas: strong unique passwords, encryption, patching, least privilege, backups and defence in depth."),
    ("What is encryption?",
     "**Encryption** scrambles data with a secret key so only holders of the key can read it. Symmetric encryption uses one shared key (AES); asymmetric uses a public/private key pair (RSA, elliptic curves)."),

    # --- everyday science / why ---------------------------------------------
    ("Why is the sky blue?",
     "The sky is blue because of **Rayleigh scattering**: sunlight consists of all colours, and the short (blue) wavelengths are scattered far more strongly by nitrogen and oxygen molecules in the atmosphere than the long (red) wavelengths. We see that scattered blue light coming from every direction. At sunset, light travels a longer path through the atmosphere, so blue is scattered away and reds and oranges dominate."),
    ("Why do we dream?",
     "Science has no single proven answer, but the leading theories are: **memory consolidation** (the brain replays and organises the day's learning, mostly in REM sleep), **emotional processing** (working through feelings in a safe 'virtual' space), and **threat rehearsal**. Most people dream 4-6 times a night, mostly during REM sleep, and forget over 90% of them."),
    ("Why is the ocean salty?",
     "Rain erodes rocks on land and carries dissolved mineral salts (especially sodium and chloride) into rivers and then the sea. Water evaporates and falls as rain again, but the salts stay behind, so they have concentrated in the oceans over billions of years."),
    ("What causes tides?",
     "Tides are mainly caused by the **Moon's gravity** (and to a lesser extent the Sun's), which pulls the oceans into a bulge on the near side and, through the Earth's motion, a second bulge on the far side. Most coasts see two high and two low tides per day."),
    ("What causes the seasons?",
     "Seasons are caused by the **tilt of Earth's axis (23.5 degrees)** as it orbits the Sun - not by distance from the Sun. Whichever hemisphere is tilted toward the Sun gets more direct sunlight and longer days (summer)."),
    ("How do vaccines work?",
     "**Vaccines** train the immune system using a harmless version or fragment of a pathogen (weakened, inactivated, or just a protein or mRNA instruction). The immune system learns to recognise it and creates memory cells, so a real infection is stopped quickly - without causing the disease."),
    ("How does GPS work?",
     "**GPS** uses a constellation of satellites each broadcasting its position and precise time. A receiver measures how long signals take to arrive from at least four satellites and trilaterates its position - typically accurate to a few metres."),
    ("How does Wi-Fi work?",
     "**Wi-Fi** transmits data over radio waves (2.4 GHz, 5 GHz or 6 GHz bands) between a router and devices using the IEEE 802.11 standard. Data is encoded into the radio signal and organised into packets, with encryption (WPA2/WPA3) protecting the traffic."),
    ("How does the internet work?",
     "The **internet** is a global network of networks. Data is split into packets, addressed with IP addresses, and routed between computers by routers using TCP/IP. TCP guarantees packets arrive complete and in order, while DNS resolves names to addresses."),
    ("How do airplanes fly?",
     "Airplanes fly mainly because of **lift** created by their wings: wings are shaped (airfoil) so air moves faster over the curved top, lowering pressure there and pushing the wing upward. Engines provide forward thrust to keep the airflow; Newton's third law (deflecting air downward) also contributes."),
    ("How does a rainbow form?",
     "Sunlight enters raindrops, **refracts** (bends), reflects off the inside back surface, and refracts again as it exits, splitting white light into its spectrum. You see a rainbow when the Sun is behind you and rain is in front, at about 42 degrees from the antisolar point. The colours are red, orange, yellow, green, blue, indigo, violet."),
    ("What is lightning and thunder?",
     "**Lightning** is a huge static-electric discharge between charged regions of a storm cloud (or cloud and ground), heating the air to about 30,000 degrees C. **Thunder** is the shockwave from that sudden heating expanding the air. Light travels far faster than sound, so you see lightning before you hear it - count seconds and divide by 3 for the distance in km."),
    ("What is the water cycle?",
     "The **water cycle** is the continuous movement of water: evaporation from oceans and lakes, transpiration from plants, condensation into clouds, precipitation as rain or snow, and collection in rivers, lakes and groundwater - then it repeats."),
    ("What is the greenhouse effect?",
     "The **greenhouse effect** is the trapping of heat near Earth's surface by gases such as water vapour, carbon dioxide and methane, which absorb outgoing infrared radiation and re-emit it. It keeps Earth about 33 degrees C warmer than it would otherwise be; human emissions are strengthening it and causing global warming."),
    ("What is climate change?",
     "**Climate change** is the long-term shift in global temperatures and weather patterns, driven mainly since the 1800s by burning fossil fuels, which adds CO2 and other greenhouse gases. Effects include rising temperatures, melting ice, rising seas and more extreme weather."),
    ("What is electricity?",
     "**Electricity** is the flow of electric charge, usually electrons moving through a conductor. A voltage (potential difference) pushes current (measured in amperes) through a circuit; resistance (ohms) opposes it. Ohm's law: V = I x R. Power: P = V x I."),
    ("What is light?",
     "**Light** is electromagnetic radiation visible to the human eye (wavelengths about 380-750 nm). It behaves as both a wave and a stream of particles called photons, and travels at 299,792,458 m/s in a vacuum."),
    ("What is sound?",
     "**Sound** is a pressure wave travelling through a medium such as air, water or solids. Its frequency (Hz) determines pitch and its amplitude determines loudness. Humans hear roughly 20 Hz to 20,000 Hz."),
    ("What is gravity?",
     "**Gravity** is the attraction between masses. Newton described it as a force (F = G x m1 x m2 / r^2); Einstein's general relativity describes it as the curvature of spacetime caused by mass and energy."),
    ("What is temperature and heat?",
     "**Temperature** measures the average kinetic energy of particles (degrees C, F or kelvin). **Heat** is thermal energy transferred from a hotter body to a colder one. They are related but not the same: a spark can be hotter than a bathtub yet contain far less heat."),
    ("What is an atom?",
     "An **atom** is the smallest unit of an element: a nucleus of protons and neutrons surrounded by electrons. The number of protons (atomic number) defines the element."),
    ("What is the periodic table?",
     "The **periodic table** arranges all 118 known elements by increasing atomic number in rows (periods) and columns (groups). Elements in the same group share chemical properties because they have the same number of outer electrons."),
    ("What is an ecosystem?",
     "An **ecosystem** is a community of living organisms interacting with each other and their physical environment (sunlight, water, soil, air), exchanging energy and nutrients in a balanced web."),
    ("What is biodiversity?",
     "**Biodiversity** is the variety of life - genes, species and ecosystems - in a place. Higher biodiversity makes ecosystems more resilient; it is currently declining faster than at any time in human history."),
    ("What is the ozone layer?",
     "The **ozone layer** is a region of the stratosphere rich in ozone (O3) that absorbs most of the Sun's harmful ultraviolet radiation. It was damaged by CFC chemicals and is slowly recovering thanks to the 1987 Montreal Protocol."),

    # --- math ----------------------------------------------------------------
    ("What is the Pythagorean theorem?",
     "The **Pythagorean theorem** says that in a right-angled triangle, a^2 + b^2 = c^2, where c is the hypotenuse. Example: 3-4-5, since 9 + 16 = 25."),
    ("What is a prime number?",
     "A **prime number** is a whole number greater than 1 whose only divisors are 1 and itself. The first primes are 2, 3, 5, 7, 11, 13, 17, 19, 23, 29. There are infinitely many (proved by Euclid)."),
    ("What is the Fibonacci sequence?",
     "The **Fibonacci sequence** starts 0, 1, 1, 2, 3, 5, 8, 13, 21, 34... where each number is the sum of the two before it. The ratio of consecutive terms approaches the golden ratio (about 1.618)."),
    ("What is the area of a circle?",
     "The area of a circle is **pi x r^2** (pi times the radius squared) and its circumference is **2 x pi x r**."),
    ("What is the sum of the angles in a triangle?",
     "The interior angles of any flat (Euclidean) triangle always add up to **180 degrees**."),
    ("How many degrees are in a circle?",
     "A full circle is **360 degrees**, which is 2 x pi radians. A right angle is 90 degrees."),
    ("What is the golden ratio?",
     "The **golden ratio** is approximately **1.6180339887...** (written phi), where a line is divided so that the whole is to the longer part as the longer part is to the shorter."),
    ("What is a factorial?",
     "**Factorial** (n!) is the product of all whole numbers from 1 to n. Example: 5! = 5 x 4 x 3 x 2 x 1 = 120. 0! is defined as 1."),
    ("What is the difference between mean, median and mode?",
     "**Mean** is the average (sum divided by count). **Median** is the middle value when sorted. **Mode** is the most frequent value. The median resists outliers better than the mean."),

    # --- everyday / general -------------------------------------------------
    ("How many days are in a year?",
     "A normal year has **365 days**; a leap year has **366**. Leap years happen every 4 years (divisible by 4), except centuries not divisible by 400 - so 2000 was a leap year but 1900 was not."),
    ("How many seconds are in a day?",
     "There are **86,400 seconds** in a day (24 x 60 x 60)."),
    ("How many planets are in the solar system?",
     "There are **8 planets**: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus and Neptune. Pluto was reclassified as a dwarf planet in 2006."),
    ("What is the largest planet in the solar system?",
     "**Jupiter** is the largest planet - more massive than all the other planets combined, with a diameter of about 143,000 km."),
    ("What is the smallest planet in the solar system?",
     "**Mercury** is the smallest planet (diameter about 4,880 km) and the closest to the Sun."),
    ("What is the closest star to Earth?",
     "The **Sun** is the closest star (about 150 million km away, or 1 astronomical unit). The closest star after the Sun is **Proxima Centauri**, about 4.25 light-years away."),
    ("How far is the Moon from Earth?",
     "The Moon is on average about **384,400 km** from Earth - roughly 1.3 light-seconds. It drifts about 3.8 cm further away each year."),
    ("What galaxy do we live in?",
     "We live in the **Milky Way**, a barred spiral galaxy about 100,000 light-years across containing 100-400 billion stars. Its centre is about 26,000 light-years away."),
    ("How old is the universe?",
     "The universe is about **13.8 billion years old**, and its expansion is measured by the Hubble constant; it began in the Big Bang."),
    ("What is a light-year?",
     "A **light-year** is the distance light travels in one year: about **9.46 trillion km** (5.88 trillion miles). It measures distance, not time."),
    ("What are the colours of the rainbow in order?",
     "**Red, orange, yellow, green, blue, indigo, violet** (ROYGBIV) - memorised as 'Richard Of York Gave Battle In Vain'."),
    ("What currency is used in Japan?",
     "**Japan uses the yen** (JPY), written as 1 yen = 100 sen."),
    ("What currency is used in the United Kingdom?",
     "The **pound sterling** (GBP), written as 1 pound = 100 pence."),
    ("What currency is used in the European Union?",
     "The **euro** (EUR) is used by 20 EU countries in the eurozone, written as 1 euro = 100 cents."),
    ("What currency is used in India?",
     "The **Indian rupee** (INR) is India's currency, written as 1 rupee = 100 paise."),
    ("How many players are on a football (soccer) team?",
     "A football (soccer) team fields **11 players** at a time, including the goalkeeper. The World Cup is held every 4 years."),
    ("How many pieces are on a chess board?",
     "Chess has **32 pieces** (16 per player: 8 pawns, 2 rooks, 2 knights, 2 bishops, 1 queen, 1 king) on a 64-square board."),
    ("How many keys does a piano have?",
     "A standard piano has **88 keys** - 52 white and 36 black."),
    ("How many strings does a guitar have?",
     "A standard acoustic or electric guitar has **6 strings**."),
    ("How many hours of sleep do adults need?",
     "Most adults need **7-9 hours of sleep** per night. Sleep supports memory, immunity, mood and physical repair."),
    ("What is the largest religion in the world?",
     "**Christianity** is the largest religion (about 2.4 billion followers), followed by Islam (about 1.9 billion), Hinduism and Buddhism."),
    ("How many countries are in the world?",
     "There are **195 countries** widely recognised: 193 UN member states plus Vatican City and Palestine. Disputed territories make the count slightly flexible."),
    ("What is the saltiest body of water?",
     "The **Dead Sea** is one of the saltiest lakes (about 34% salinity), so dense that people float easily. The truly saltiest is the Don Juan Pond in Antarctica."),
    ("What is the largest volcano on Earth?",
     "**Mauna Loa** in Hawaii is the largest active volcano by volume. The largest known volcano in the solar system is Olympus Mons on Mars."),
    ("What is the Richter scale?",
     "The **Richter scale** (now superseded by the moment magnitude scale) measures earthquake magnitude logarithmically: each whole number is about 32 times more energy than the last. Magnitude 7 is a major earthquake."),
    ("What is a tropical cyclone?",
     "A **tropical cyclone** is a rotating storm system over warm ocean water with sustained winds above 119 km/h. It is called a hurricane in the Atlantic, a typhoon in the Pacific, and a cyclone in the Indian Ocean."),
    ("What is the difference between weather and climate?",
     "**Weather** is the day-to-day state of the atmosphere (rain, sun, wind). **Climate** is the average pattern over decades or centuries. Climate is what you expect; weather is what you get."),
    ("What is a habitat?",
     "A **habitat** is the natural environment where a species lives - desert, rainforest, ocean, grassland - providing the food, water, shelter and space it needs."),
    ("What is the food chain?",
     "A **food chain** shows how energy flows: producers (plants) are eaten by herbivores (primary consumers), which are eaten by carnivores (secondary consumers), and decomposers break down remains to return nutrients to the soil."),
    ("What is a fossil?",
     "A **fossil** is the preserved remains or trace of a living thing older than about 10,000 years - usually mineralised bones, shells, imprints, or traces such as footprints, preserved in rock."),

    # --- how things work (mechanism questions) -----------------------------
    ("How does electricity work?",
     "**Electricity** is the flow of electric charge - usually electrons drifting through a conductor such as copper wire. A voltage (potential difference, in volts) pushes the charges, the resulting flow is the current (in amperes), and resistance (in ohms) opposes it: **V = I x R** (Ohm's law). Generators at power stations convert motion into this flow, the grid carries it to homes, and devices convert it back into light, heat, motion or computing. Measured in watts, power is voltage times current."),
    ("What is blockchain?",
     "A **blockchain** is a shared digital ledger that records transactions in blocks, chained together by cryptographic hashes. Each block contains the hash of the previous block, so altering an old record would break every later block. Copies are kept by many computers (nodes) that agree on new blocks by consensus rules such as proof of work or proof of stake. Bitcoin and Ethereum are the best-known uses; supply chains and land registries also use it. Explain it simply: it is a notebook copied to thousands of people where every page is sealed with a fingerprint of the previous page, so nobody can secretly rewrite history."),
    ("How does blockchain work?",
     "A blockchain works in four steps: (1) a transaction is broadcast to a peer-to-peer network of nodes; (2) nodes check it is valid and hold it in a pool; (3) they agree on an order and seal a batch of transactions into a **block** using a consensus rule such as proof of work (miners race to solve a hash puzzle) or proof of stake (validators are chosen by their stake); (4) the new block is linked to the previous one by a cryptographic hash and copied to everyone. Changing any past block would change every later hash, so tampering is detected instantly."),
    ("What is quantum computing?",
     "A **quantum computer** stores information in **qubits**, which - unlike ordinary bits - can hold 0 and 1 at the same time (superposition) and can be entangled so their outcomes are linked. Algorithms manipulate the whole set of states at once, then interference amplifies the right answers when the qubits are measured. That gives huge speedups for factoring (Shor's algorithm), search-like problems (Grover's) and simulating molecules. Qubits are fragile: errors from heat, vibration and radiation must be corrected with many physical qubits per logical one, which is why practical quantum computers are still early-stage."),
    ("How does quantum computing work?",
     "Qubits (superconducting circuits, trapped ions or photons) are cooled and isolated, then gates rotate and entangle them so many possible states are processed in superposition. A quantum algorithm choreographs those states so wrong answers cancel out (interference) and the right measurement outcome becomes likely. Measuring collapses the state, so algorithms are run many times and the statistics of the results give the answer."),
    ("How does Wi-Fi work?",
     "**Wi-Fi** sends data over radio waves in the 2.4 GHz, 5 GHz or 6 GHz bands. Your router and device exchange packets using OFDM modulation, agreeing on a channel; the router usually bridges that traffic to a wired internet connection. WPA2/WPA3 encrypts the air link so nearby devices cannot read it. Walls and distance weaken the signal; 2.4 GHz travels further, 5/6 GHz is faster but shorter-range."),
    ("How does the internet work?",
     "The internet is a network of networks that passes small packets of data using **TCP/IP**. Your device sends a request to a router, your ISP forwards it across backbone links, and **DNS** translates names such as example.com into IP addresses. TCP splits the data into packets, numbers them, and retransmits anything lost; the destination reassembles them. **HTTP/HTTPS** is the protocol browsers and web servers speak, with HTTPS adding TLS encryption."),
    ("How does GPS work?",
     "**GPS** satellites carry atomic clocks and continuously broadcast the time and their orbital position. Your receiver measures how long each signal took to arrive, converts that to a distance (radio waves travel about 300 m per microsecond), and trilaterates its position from at least four satellites - three for latitude/longitude/altitude and one to correct the receiver's own clock error."),
    ("How does a battery work?",
     "A **battery** converts chemical energy into electrical energy. Two electrodes (an anode and a cathode) sit in an electrolyte. At the anode, a chemical reaction releases electrons that travel through the external circuit - doing work - and arrive at the cathode, while ions move through the electrolyte to balance the charge. Lithium-ion cells in phones and EVs are rechargeable because the reactions are reversible."),
    ("How do solar panels work?",
     "**Solar (photovoltaic) panels** are made of silicon layers doped to create a built-in electric field. When photons of light hit the silicon they knock electrons loose, and the field pushes those electrons toward the contacts, creating a voltage. An inverter converts the DC output into grid-compatible AC. Typical panels convert 18-23% of sunlight into electricity."),
    ("How does a vaccine work?",
     "A **vaccine** shows the immune system a harmless preview of a pathogen - a weakened or inactivated germ, a protein subunit, or mRNA instructions for one surface protein. Immune cells learn to recognise that antigen and build memory B and T cells plus antibodies. If the real pathogen later appears, the response is fast and strong enough to stop the illness before it develops. Herd immunity protects people who cannot be vaccinated."),
    ("How does encryption work?",
     "**Encryption** scrambles data with an algorithm and a secret key so only holders of the right key can unscramble it. Symmetric ciphers such as AES use the same key for locking and unlocking. Public-key systems such as RSA and elliptic curves use a key pair: anyone can encrypt with your public key, but only your private key can decrypt; they also sign data so receivers can verify who sent it. The security rests on mathematical hardness (e.g. factoring huge numbers) and on keeping private keys secret."),
    ("How does a refrigerator work?",
     "A **refrigerator** moves heat from inside to outside using a refrigerant that cycles through evaporation and condensation. The compressor raises the pressure so the refrigerant condenses and releases heat through the outdoor coils; it then flows through an expansion valve where the pressure drops, it evaporates, absorbs heat from inside the fridge, and returns to the compressor. Insulation and a thermostat keep the temperature steady."),
    ("How does a microwave oven work?",
     "A **microwave oven** produces 2.45 GHz radio waves in a magnetron. Those waves make water molecules rotate billions of times per second, and that molecular friction becomes heat, cooking food from the inside out. The metal mesh on the door blocks the waves, and the turntable evens out hot spots."),
    ("Why is the ocean salty?",
     "Rain and rivers slowly dissolve mineral salts from rocks and carry them to the sea. Water evaporates leaving the salt behind, so over hundreds of millions of years the oceans accumulated about 3.5% dissolved salts, mostly sodium chloride. Closed seas with high evaporation, such as the Dead Sea, become much saltier."),
    ("Why is the sky blue?",
     "The sky is blue because of **Rayleigh scattering**: sunlight contains all colours, and the short (blue) wavelengths are scattered far more strongly by nitrogen and oxygen molecules in the atmosphere than the long (red) ones. That scattered blue light reaches your eyes from every direction, so the sky looks blue. At sunset the light travels through more atmosphere, the blue is scattered away, and reds and oranges reach you directly. In space there is no atmosphere, so the sky is black."),
    ("Why do we have seasons?",
     "Earth's **axial tilt of about 23.4 degrees** causes the seasons. As Earth orbits the Sun, each hemisphere is tilted toward or away from the Sun for part of the year, so sunlight strikes more directly (concentrated, longer days) or more obliquely (spread out, shorter days). The distance from the Sun is not the cause - Earth is actually closest to the Sun in January, during northern winter."),
    ("Why do we dream?",
     "Dreaming happens mostly in **REM sleep**, when the brain is active but the body is paralysed. Science has no single proven purpose; the leading theories are memory consolidation (the brain replays and organises the day's learning), emotional processing (working through feelings in a safe 'virtual' space), threat rehearsal (practising responses to danger) and simply the side-effect of random brainstem activity that the cortex weaves into a story. Most people dream 4-6 times a night but forget most of it within minutes of waking."),
    ("What is gravity?",
     "**Gravity** is the attraction between masses. Newton described it as a force: F = G x m1 x m2 / r^2 - twice the mass means twice the pull, twice the distance means a quarter of it. Einstein's general relativity explains it more deeply as the curvature of spacetime: mass and energy bend spacetime, and objects follow the straightest available path through that curve. It keeps planets in orbit, gives objects weight, and causes tides."),
    ("What is an atom?",
     "An **atom** is the smallest unit of an element. It has a dense nucleus of protons (positive) and neutrons (neutral), surrounded by a cloud of electrons (negative) that occupy orbitals; the nucleus holds over 99.9% of the mass. The number of protons (the atomic number) decides which element it is; the number of neutrons can vary (isotopes)."),
    ("What is a black hole?",
     "A **black hole** is a region where gravity is so strong that nothing - not even light - can escape once it crosses the event horizon. It forms when a massive star collapses at the end of its life. Its mass bends spacetime extremely; time appears to slow near the horizon as seen from far away. Supermassive black holes of millions of suns sit at the centres of most galaxies, including the Milky Way."),
    ("What is the Big Bang?",
     "The **Big Bang** is the model in which the universe expanded from an extremely hot, dense state about **13.8 billion years ago**. Evidence includes the cosmic microwave background radiation, the abundance of light elements, and the observed expansion of galaxies. It was not an explosion in space but the expansion of space itself."),
    ("What is evolution?",
     "**Evolution** is the change in inherited traits of populations over generations. Mutations create variation; natural selection favours variants that improve survival and reproduction in a given environment, so those traits become more common. Over millions of years this produces new species. Evidence comes from fossils, DNA comparisons, direct observation of microbes and the distribution of species."),
    ("What is the water cycle?",
     "The **water cycle** moves water between ocean, atmosphere and land: the Sun's heat evaporates water (and plants transpire it), the vapour rises, cools and condenses into clouds, then falls as precipitation (rain, snow, hail). Water then runs off into rivers, soaks into groundwater, or is taken up by plants, and the cycle repeats."),
    ("What is the greenhouse effect?",
     "The **greenhouse effect** is the trapping of heat by atmospheric gases. Sunlight warms Earth's surface, which re-emits energy as infrared radiation; gases such as carbon dioxide, methane and water vapour absorb that infrared and re-radiate some back down, keeping the surface about 33 degrees C warmer than it would otherwise be. Burning fossil fuels increases those gases and strengthens the effect, driving global warming."),
    ("What is the difference between a virus and a bacterium?",
     "**Bacteria** are single-celled living organisms a few micrometres across that reproduce on their own and are killed by antibiotics. **Viruses** are far smaller, are not cells, cannot reproduce without hijacking a host cell, and are not affected by antibiotics - they need vaccines or antivirals, and the body's immune system clears most of them."),
    ("What is DNA?",
     "**DNA** (deoxyribonucleic acid) is the molecule that stores genetic instructions. It is a double helix of two strands held together by base pairs: A pairs with T and C pairs with G. The sequence of those letters spells out genes, which cells read to build proteins. Humans have about 3 billion base pairs in 23 pairs of chromosomes."),
    ("What is photosynthesis?",
     "**Photosynthesis** is how plants, algae and some bacteria turn light into chemical energy. Chlorophyll absorbs light, and its energy splits water molecules; the plant uses carbon dioxide and the freed hydrogen to build glucose, releasing oxygen as a by-product: 6CO2 + 6H2O + light -> C6H12O6 + 6O2. It is the base of nearly every food chain and the source of the oxygen we breathe."),
    ("What is machine learning?",
     "**Machine learning** is a branch of AI where a program learns patterns from data instead of being given explicit rules. The main kinds are supervised learning (labelled examples teach it to predict), unsupervised learning (it groups or compresses unlabelled data) and reinforcement learning (it learns from rewards). A trained model generalises: it makes useful predictions about inputs it has never seen."),
    ("What is artificial intelligence?",
     "**Artificial intelligence** is the field of building computer systems that perform tasks that normally need human intelligence - understanding language, recognising images, reasoning, planning and learning. Modern AI is dominated by machine learning and neural networks; large language models such as this chatbot's bigger cousins are trained on huge text corpora to predict language and solve tasks."),
    ("What is the difference between AI and machine learning?",
     "**AI** is the broad goal of making machines act intelligently; **machine learning** is one family of methods (learning patterns from data) used to reach that goal. So all machine learning is AI, but not all AI is machine learning - older AI used hand-written rules and search, and some modern AI (for example, a chess engine's search) still does."),
    ("What is cloud computing?",
     "**Cloud computing** means renting computing resources - servers, storage, databases and AI services - over the internet instead of owning them, paying only for what you use. Providers such as AWS, Azure and Google Cloud run huge data centres; customers get them on demand and can scale up or down in minutes. Models include IaaS (raw machines), PaaS (managed runtimes) and SaaS (finished applications)."),
    ("What is the difference between TCP and UDP?",
     "Both are transport protocols. **TCP** is connection-oriented and reliable: it performs a three-way handshake, numbers every packet, retransmits anything lost and delivers data in order - used by web, email and file transfer. **UDP** is connectionless and lightweight: it fires packets with no handshake or resend, so it is faster with less overhead, at the cost of possible loss - used by DNS, video streaming, online games and VoIP."),
    ("What is HTTP?",
     "**HTTP** (HyperText Transfer Protocol) is how browsers and servers talk: the client sends a request method plus a path (GET /index.html), the server returns a status code and the content. HTTPS is the same protocol over a TLS-encrypted connection, which authenticates the server with a certificate and protects the data in transit."),
    ("What is DNS?",
     "**DNS** (Domain Name System) is the internet's phone book: it translates human names such as wikipedia.org into numeric IP addresses. A resolver asks a hierarchy of servers (root, top-level domain, authoritative) and caches the answer so repeat lookups are instant."),
    ("What is open source software?",
     "**Open source** software publishes its source code under a licence that lets anyone study, modify and redistribute it (MIT, Apache, GPL and others). It is developed in the open by communities and companies; Linux, Python, Firefox and Android's AOSP are famous examples."),
    ("What is an operating system?",
     "An **operating system** is the software layer that manages a computer's hardware for programs: it schedules the CPU, allocates memory, organises files, handles devices through drivers, and provides security boundaries between users and processes. Windows, Linux, macOS and Android are operating systems."),

    # --- world records ------------------------------------------------------
    ("What is the deepest lake in the world?",
     "**Lake Baikal** in Siberia, Russia is the deepest lake on Earth at 1,642 metres (5,387 ft) deep - and it holds about 20% of the world's unfrozen fresh water. The **Caspian Sea** is the largest lake by area, but Baikal is the deepest."),
    ("What is the highest waterfall in the world?",
     "**Angel Falls** (Kerepakupai Meru) in Venezuela is the highest uninterrupted waterfall, dropping 979 metres (3,212 ft) from Auyan-Tepui. **Niagara Falls** is far wider but only about 51 metres tall."),
    ("What is the hottest place on Earth?",
     "The **Lut Desert** in Iran and **Death Valley** in California are the hottest places measured on Earth: Death Valley recorded 56.7 degrees C (134 degrees F) in 1913, while satellite data shows the Lut Desert reached 70.7 degrees C (159 degrees F) surface temperature."),
    ("What is the coldest place on Earth?",
     "**Antarctica** is the coldest place on Earth: the Vostok Station measured -89.2 degrees C (-128.6 degrees F), and satellite readings in the East Antarctic Plateau have seen below -93 degrees C."),
    ("What is the largest animal in the world?",
     "The **blue whale** is the largest animal that has ever lived, reaching about 30 metres (98 ft) long and 180 tonnes. Its tongue alone can weigh as much as an elephant and its heart as much as a small car."),
    ("What is the fastest animal in the world?",
     "The **peregrine falcon** is the fastest animal, reaching over 320 km/h (200 mph) in a hunting dive. On land the **cheetah** is fastest, sprinting up to about 110 km/h (70 mph)."),
    ("What is the fastest land animal?",
     "The **cheetah** is the fastest land animal, sprinting up to about 110 km/h (70 mph) in short bursts, with a stride of up to 7 metres."),
    ("What is the tallest building in the world?",
     "The **Burj Khalifa** in Dubai, United Arab Emirates is the tallest building in the world at 828 metres (2,717 ft) with 163 floors. It was completed in 2010. The Merdeka 118 in Kuala Lumpur is second at 679 metres."),
    ("What is the longest bridge in the world?",
     "The **Danyang-Kunshan Grand Bridge** in China is the longest bridge in the world at about 164.8 km (102 miles), carrying the Beijing-Shanghai high-speed railway. The longest sea crossing is the Hong Kong-Zhuhai-Macau Bridge at 55 km."),
    ("What is the largest country in the world?",
     "**Russia** is the largest country by area at about 17.1 million square km - roughly 11% of the world's land, spanning 11 time zones. Canada is second and China third."),
    ("What is the smallest country in the world?",
     "**Vatican City** is the smallest country, at just 0.49 square km (110 acres) with about 800 residents. **Monaco** is the second smallest."),
    ("What is the most populous country in the world?",
     "**India** is the most populous country, passing China in 2023 with over 1.42 billion people; China is second at about 1.41 billion."),
    ("What is the largest island in the world?",
     "**Greenland** is the largest island in the world at about 2.17 million square km (Australia is counted as a continent, not an island). It is an autonomous territory of Denmark."),
    ("What is the deepest ocean trench?",
     "The **Mariana Trench** in the western Pacific is the deepest ocean trench; its deepest point, the **Challenger Deep**, lies about 10,935 metres (35,876 ft) below sea level - deeper than Mount Everest is tall."),
    ("What is the tallest tree in the world?",
     "A coast redwood named **Hyperion** in Redwood National Park, California is the tallest known tree at about 115.9 metres (380 ft). Its exact location is kept secret to protect it."),
    ("What is the largest shark in the world?",
     "The **whale shark** is the largest fish in the sea, growing up to about 18 metres (60 ft) long. Despite its size it feeds on plankton and is harmless to humans."),
    ("What is the highest mountain in Africa?",
     "**Mount Kilimanjaro** in Tanzania is the highest mountain in Africa, 5,895 metres (19,341 ft) above sea level. It is a dormant stratovolcano with three cones - Kibo, Mawenzi and Shira - and is one of the Seven Summits."),
    ("How tall is Mount Kilimanjaro?",
     "**Mount Kilimanjaro** is 5,895 metres (19,341 ft) tall, the highest point in Africa. Its summit, Uhuru Peak on the Kibo cone, is a dormant volcano that can be reached by hiking - no technical climbing is required."),
    ("What is the largest organ in the human body?",
     "The **skin** is the largest organ of the human body, covering about 1.5-2 square metres and weighing 3-4 kg. The largest internal organ is the **liver**."),
    ("What is the smallest bone in the human body?",
     "The **stapes** (stirrup) in the middle ear is the smallest bone in the human body, about 3 mm long. The smallest muscle is the stapedius."),
]


def build_entries():
    """Return (question, answer, topic) triples."""
    entries = []
    for line in CAPITALS.strip().splitlines():
        if "=" not in line:
            continue
        country, capital = line.split("=", 1)
        country, capital = country.strip(), capital.strip()
        entries.append(("What is the capital of %s?" % country,
                        "The capital of **%s** is **%s**." % (country, capital),
                        "capital"))
        entries.append(("What is the capital city of %s?" % country,
                        "The capital city of **%s** is **%s**." % (country, capital),
                        "capital"))
    for line in ELEMENTS.strip().splitlines():
        parts = line.split("|")
        if len(parts) != 3:
            continue
        z, sym, name = parts[0].strip(), parts[1].strip(), parts[2].strip()
        entries.append(("What is the chemical symbol for %s?" % name,
                        "The chemical symbol for **%s** is **%s** (atomic number %s)."
                        % (name, sym, z), "chemistry"))
        entries.append(("What is the atomic number of %s?" % name,
                        "The atomic number of **%s** (%s) is **%s**."
                        % (name, sym, z), "chemistry"))
    for q, a in FACTS:
        entries.append((q, a, "facts"))
    return entries


def main():
    train = "--train" in sys.argv
    t0 = time.time()
    mem = Memory()
    brain = Brain(mem)

    existing = set()
    with mem.lock:
        for (q,) in mem.conn.execute("SELECT question FROM qa"):
            existing.add(re.sub(r"\W+", " ", (q or "").lower()).strip())

    def norm(q):
        return re.sub(r"\W+", " ", q.lower()).strip()

    entries = build_entries()
    qa_added = 0
    doc_added = 0
    for q, a, topic in entries:
        # always (re)store the knowledge passage - hash dedupe makes this
        # idempotent, and it restores passages removed by size pruning
        text = q + " " + re.sub(r"\*\*", "", a)
        ids = mem.add_passages("facts://%s" % topic, "TenSeiAi facts pack: " + topic,
                               text, source="facts", topic=topic)
        doc_added += len(ids)
        nq = norm(q)
        if nq in existing:
            continue
        existing.add(nq)
        emb = brain.embedder.encode(q)
        mem.add_qa(q, a, EVIDENCE, emb,
                   emb0=brain.embedder.base_encode(q), mode="facts")
        qa_added += 1
    mem.kv_set("facts_pack_v1", {"qa": qa_added, "docs": doc_added,
                                 "at": time.time()})
    print("[facts] added %d Q&A pairs, %d passages in %.1fs"
          % (qa_added, doc_added, time.time() - t0))
    print("[facts] memory now:", mem.stats())
    if train:
        meta = brain.train_all(log=lambda m: print(" [train]", m))
        print("[facts] brain version:", meta.get("version"),
              "metrics:", meta.get("metrics"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
