"""
Seeds authoritative multi-domain knowledge into TenSeiAi's database.
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tensei.memory import Memory
from tensei.embed import Embedder

ENTRIES = [
    # --- Science & Physics ---
    {
        "q": "Explain the first and second laws of thermodynamics.",
        "a": "**First and Second Laws of Thermodynamics:**\n\n"
             "1. **First Law of Thermodynamics (Law of Conservation of Energy):**\n"
             "Energy cannot be created or destroyed in an isolated system; it can only change form or be transferred between systems and surroundings. The change in internal energy ($\\Delta U$) of a closed system equals the heat added ($Q$) minus the work done by the system ($W$):\n"
             "$$\\Delta U = Q - W$$\n\n"
             "2. **Second Law of Thermodynamics (Entropy Law):**\n"
             "In any spontaneous thermodynamic process, the total **entropy** of an isolated system always increases over time ($\\Delta S_{\\text{total}} \\ge 0$). Heat flows spontaneously from hotter bodies to colder bodies and never in reverse without external work, meaning all natural macroscopic processes are irreversible and maximum thermal efficiency is fundamentally bounded (Carnot limit)."
    },
    {
        "q": "What causes ocean tides on Earth?",
        "a": "**Ocean tides** are caused primarily by the **gravitational attraction of the Moon and the Sun** acting on Earth's oceans, combined with the rotation of the Earth.\n\n"
             "1. **Lunar Gravitational Pull:** The Moon exerts a differential gravitational pull across the Earth. Ocean waters on the side facing the Moon are pulled outward toward it (direct high tide), while ocean waters on the opposite side experience the weakest pull, creating a second outward tidal bulge (antipodal high tide).\n"
             "2. **Solar Influence:** The Sun also exerts tidal forces (~46% as strong as the Moon). When the Earth, Moon, and Sun align during New and Full Moons, their gravitational forces reinforce each other producing maximum tidal range (**Spring tides**). When at right angles during quarter moons, they partially cancel, producing minimum tidal range (**Neap tides**).\n"
             "3. **Earth's Rotation:** As Earth rotates on its axis through these two tidal bulges every 24 hours and 50 minutes (a lunar day), most coastal areas experience two high tides and two low tides each day (semidiurnal tides)."
    },
    {
        "q": "What is absolute zero in Celsius and Kelvin?",
        "a": "**Absolute zero** is the theoretical lowest possible temperature where fundamental particles have minimal thermal motion (zero classical kinetic energy).\n\n"
             "- In **Kelvin**: **0 K**\n"
             "- In **Celsius**: **-273.15 °C**\n"
             "- In **Fahrenheit**: **-459.67 °F**\n\n"
             "At absolute zero, thermodynamic entropy reaches its minimum value according to the Third Law of Thermodynamics. While systems cannot be cooled strictly to 0 K due to quantum zero-point fluctuations, physicists have cooled atoms to within fractions of a nanokelvin."
    },
    {
        "q": "What is Bernoulli's principle and how does it explain aerodynamic lift in airplanes?",
        "a": "**Bernoulli's principle** states that an increase in the speed of a fluid occurs simultaneously with a decrease in static pressure or a decrease in the fluid's potential energy ($P + \\frac{1}{2}\\rho v^2 + \\rho g h = \\text{constant}$).\n\n"
             "**How it explains aerodynamic lift:**\n"
             "1. **Airfoil Camber:** An airplane wing (airfoil) is curved on top and flatter on the bottom.\n"
             "2. **Velocity Differential:** Air flowing over the upper curved surface must accelerate, traveling at higher velocity than air underneath.\n"
             "3. **Pressure Differential:** According to Bernoulli's principle, higher velocity over the top creates lower static pressure above the wing compared to the higher static pressure beneath the wing.\n"
             "4. **Net Aerodynamic Lift:** This pressure differential generates a net upward force (lift) that pushes the wing upward into the lower-pressure zone, enabling flight (further complemented by Newton's Third Law downward deflection of airflow)."
    },
    {
        "q": "What is the Doppler effect?",
        "a": "The **Doppler effect** (or Doppler shift) is the observed change in frequency and wavelength of a wave resulting from relative motion between the wave source and an observer.\n\n"
             "- **Approaching Source:** As a sound or light source approaches an observer, each successive wave crest is emitted closer to the observer, compressing the observed wavelength and increasing the observed frequency (higher pitch in sound, **blueshift** in light).\n"
             "- **Receding Source:** As the source moves away, wave crests are emitted further apart, stretching the observed wavelength and decreasing the observed frequency (lower pitch in sound, **redshift** in light).\n\n"
             "It is widely used in radar speed guns, Doppler ultrasound in medicine, and astrophysics to measure the radial velocity of stars and expansion of galaxies."
    },
    {
        "q": "What is dark matter and dark energy in modern cosmology?",
        "a": "**Dark matter** and **dark energy** make up roughly 95% of the total mass-energy content of the universe, yet neither interacts directly with electromagnetic radiation (light).\n\n"
             "1. **Dark Matter (~27% of Universe):** An invisible form of matter that does not emit, absorb, or reflect light. Its existence is inferred from gravitational effects on visible matter, such as galaxy rotation curves, gravitational lensing of background light, and cosmic web formation. Leading candidates include WIMPs (Weakly Interacting Massive Particles) and axions.\n"
             "2. **Dark Energy (~68% of Universe):** A homogeneous, repulsive energy density permeating all of space that drives the accelerating expansion of the universe. In Einstein's field equations of General Relativity, it is modeled mathematically as the **Cosmological Constant ($\\Lambda$)**, acting as negative pressure across cosmic scales.\n"
             "3. **Ordinary (Baryonic) Matter** accounts for only ~5% of the universe (stars, planets, gas, and living organisms)."
    },
    {
        "q": "How does a laser work and what does the acronym LASER stand for?",
        "a": "The acronym **LASER** stands for **Light Amplification by Stimulated Emission of Radiation**.\n\n"
             "**How a Laser Works (3 Core Steps):**\n"
             "1. **Pumping & Population Inversion:** An external energy source (optical flash, electrical current) energizes electrons in a gain medium (crystal, gas, or semiconductor) from their ground state to a higher excited energy state, establishing a *population inversion* where more atoms are excited than unexcited.\n"
             "2. **Stimulated Emission:** When an incident photon of matching energy passes an excited atom, it stimulates the electron to drop back to ground state, releasing an identical secondary photon with the exact same wavelength, phase, direction, and polarization.\n"
             "3. **Optical Cavity Resonance:** Two mirrors at either end of the laser cavity (one 100% reflective, one partially transmissive) bounce photons back and forth, amplifying the cascade into an intense, coherent, monochromatic, and highly directional beam of laser light."
    },
    {
        "q": "What is Heisenberg's uncertainty principle in quantum mechanics?",
        "a": "**Heisenberg's Uncertainty Principle** is a fundamental theorem in quantum mechanics stating that certain pairs of physical properties - most famously position ($x$) and momentum ($p$) - cannot simultaneously be measured with arbitrary precision.\n\n"
             "**Mathematical Formulation:**\n"
             "$$\\Delta x \\cdot \\Delta p \\ge \\frac{\\hbar}{2}$$\n"
             "where $\\Delta x$ is uncertainty in position, $\\Delta p$ is uncertainty in momentum, and $\\hbar = \\frac{h}{2\\pi}$ is the reduced Planck constant.\n\n"
             "- The more precisely the position of a subatomic particle is known, the less precisely its momentum can be known, and vice versa.\n"
             "- This is not an experimental measurement limitation, but an intrinsic mathematical property of wave-particle duality and Fourier conjugate variables in quantum physics."
    },
    {
        "q": "What causes earthquakes and how does plate tectonics work?",
        "a": "**Earthquakes** are caused by the sudden release of accumulated strain energy in the Earth's crust, which generates seismic waves radiating outward from the rupture point (hypocenter or focus).\n\n"
             "**Plate Tectonics Mechanism:**\n"
             "1. **Lithospheric Plates:** The Earth's outermost shell (lithosphere) is fragmented into approximately 15 major tectonic plates that float and slowly drift atop the ductile, semi-fluid asthenosphere driven by mantle convection currents.\n"
             "2. **Plate Boundaries:**\n"
             "   - **Transform boundaries:** Plates slide past each other horizontally (e.g., San Andreas Fault).\n"
             "   - **Convergent boundaries:** Plates collide; one plate subducts beneath another into the mantle (forming trenches, mountains, and deep earthquakes).\n"
             "   - **Divergent boundaries:** Plates pull apart (forming mid-ocean ridges).\n"
             "3. **Elastic Rebound:** Friction locks the plates at faults while plate motion continues, building up immense shear stress. When stress exceeds rock strength, fault surfaces suddenly slip, releasing seismic waves (P-waves, S-waves, Surface waves) that shake the ground."
    },
    {
        "q": "How does radioactive decay and half-life work?",
        "a": "**Radioactive decay** is the spontaneous process by which an unstable atomic nucleus loses energy by emitting ionizing radiation (such as alpha particles, beta particles, or gamma ray photons), transforming into a more stable nuclide.\n\n"
             "**Half-Life ($t_{1/2}$):**\n"
             "The half-life of a radioactive isotope is the time required for exactly half of the radioactive nuclei in a sample to decay.\n\n"
             "**Decay Equation:**\n"
             "$$N(t) = N_0 \\left(\\frac{1}{2}\\right)^{\\frac{t}{t_{1/2}}} = N_0 e^{-\\lambda t}$$\n"
             "where $N_0$ is initial quantity, $N(t)$ is remaining quantity at time $t$, and $\\lambda = \\frac{\\ln 2}{t_{1/2}}$ is the decay constant.\n\n"
             "- Radioactive decay is a first-order stochastic process: individual decay events are random, but large populations decay with exact mathematical predictability, enabling carbon-14 dating and radiometric geochronology."
    },
    {
        "q": "What is the difference between kinetic energy and potential energy?",
        "a": "**Kinetic energy** and **potential energy** are the two fundamental forms of mechanical energy:\n\n"
             "1. **Kinetic Energy ($KE$):** The energy possessed by an object due to its **motion**.\n"
             "   - Formula: $KE = \\frac{1}{2} m v^2$ (where $m$ is mass, $v$ is velocity).\n"
             "   - Examples: A speeding car, flowing river water, a thrown baseball, thermal motion of molecules.\n\n"
             "2. **Potential Energy ($PE$):** The **stored** energy possessed by an object due to its position, state, or configuration relative to a force field.\n"
             "   - Gravitational PE Formula: $PE = m g h$ (where $g$ is gravitational acceleration, $h$ is height).\n"
             "   - Elastic PE Formula: $PE = \\frac{1}{2} k x^2$ (compressed or stretched spring).\n"
             "   - Examples: A boulder resting on a cliff, drawn bowstring, water behind a dam.\n\n"
             "By the **Law of Conservation of Energy**, kinetic and potential energy continuously convert into each other (e.g., in a swinging pendulum or falling object) while total mechanical energy remains constant ($E_{\\text{total}} = KE + PE$)."
    },
    {
        "q": "What is Archimedes' principle of buoyancy?",
        "a": "**Archimedes' Principle** states that any object completely or partially submerged in a fluid experiences an upward **buoyant force** equal in magnitude to the **weight of the fluid displaced** by the object.\n\n"
             "**Mathematical Formula:**\n"
             "$$F_b = \\rho_{\\text{fluid}} \\cdot V_{\\text{displaced}} \\cdot g$$\n"
             "where:\n"
             "- $F_b$ is the upward buoyant force (Newtons),\n"
             "- $\\rho_{\\text{fluid}}$ is the density of the fluid ($kg/m^3$),\n"
             "- $V_{\\text{displaced}}$ is the volume of submerged object / displaced fluid ($m^3$),\n"
             "- $g$ is acceleration due to gravity ($9.81 m/s^2$).\n\n"
             "**Floating vs. Sinking:**\n"
             "- If the object's average density is less than the fluid's density ($F_b > \\text{Weight}$), it floats.\n"
             "- If the object's density equals fluid density, it achieves neutral buoyancy.\n"
             "- If the object's density exceeds fluid density ($F_b < \\text{Weight}$), it sinks."
    },

    # --- Biology & Animals ---
    {
        "q": "How do vaccines stimulate the human immune system?",
        "a": "**Vaccines** train and stimulate the human immune system to recognize and fight pathogens (viruses or bacteria) without causing the disease itself.\n\n"
             "1. **Antigen Introduction:** The vaccine delivers an antigen (weakened/inactivated pathogen, recombinant protein subunit, or mRNA encoding a target surface protein like the spike protein).\n"
             "2. **Immune Activation:** Antigen-presenting cells (APCs like dendritic cells) engulf the antigen and display fragments to helper T cells ($CD4^+$).\n"
             "3. **Antibody Production:** Helper T cells activate B lymphocytes, which differentiate into plasma cells that produce specific **neutralizing antibodies** tailored to bind and neutralize the pathogen.\n"
             "4. **Long-Term Immunological Memory:** Crucially, a subset of B and T cells become **Memory B cells and Memory T cells** that persist in lymph nodes for years. If the real pathogen invades later, memory cells launch an immediate, massive secondary immune response that eliminates the infection before illness develops."
    },
    {
        "q": "What is the fastest land animal and what speed can it reach?",
        "a": "The **cheetah** (*Acinonyx jubatus*) is the fastest land animal on Earth.\n\n"
             "- **Top Speed:** Capable of reaching sprint speeds of **60 to 75 mph** (**97 to 120 km/h**).\n"
             "- **Acceleration:** Can accelerate from 0 to 60 mph in just **3 seconds** - faster than most high-performance sports cars.\n"
             "- **Anatomical Adaptations:** Flexible spine, oversized nasal passages and heart for rapid oxygen intake, non-retractable claws providing traction like athletic cleats, and a long muscular tail acting as a rudder for high-speed turns."
    },
    {
        "q": "Why and how do chameleons change their color?",
        "a": "**Why Chameleons Change Color:**\n"
             "Contrary to popular myth, chameleons primarily change color for **social communication** (courtship, dominance displays, aggression) and **thermoregulation** (darker shades to absorb solar heat, lighter shades to reflect radiation), with camouflage being a secondary benefit.\n\n"
             "**How They Change Color (Physiology):**\n"
             "1. **Iridophores & Photonic Nanocrystals:** Dermal cells called *iridophores* contain microscopic guanine nanocrystals arranged in an ordered geometric lattice.\n"
             "2. **Lattice Tuning:** By tightening or relaxing the spacing between these nanocrystals, chameleons alter the wavelength of light reflected (tight lattice reflects blue light; relaxed lattice reflects yellow and red light).\n"
             "3. **Chromatophores & Melanin:** Underneath, *melanophores* disperse or aggregate dark melanin granules to control brightness and saturation, mixing with yellow/red xanthophores to produce vibrant greens, yellows, blues, and blacks."
    },
    {
        "q": "How does cellular respiration generate energy in living organisms?",
        "a": "**Cellular respiration** is the biochemical process through which cells oxidize glucose and other nutrients to produce **ATP (adenosine triphosphate)**, the universal energy currency of life.\n\n"
             "**Overall Chemical Equation:**\n"
             "$$\\text{C}_6\\text{H}_{12}\\text{O}_6 + 6\\text{O}_2 \\rightarrow 6\\text{CO}_2 + 6\\text{H}_2\\text{O} + \\approx 36\\text{–}38\\text{ ATP}$$\n\n"
             "**Four Key Stages:**\n"
             "1. **Glycolysis (Cytoplasm):** 1 glucose molecule is cleaved into 2 pyruvate molecules, yielding net 2 ATP and 2 NADH (anaerobic).\n"
             "2. **Pyruvate Decarboxylation (Mitochondrial Matrix):** Pyruvate is converted to Acetyl-CoA, producing NADH and releasing $\\text{CO}_2$.\n"
             "3. **Krebs Cycle / Citric Acid Cycle (Mitochondrial Matrix):** Acetyl-CoA is oxidized, generating electron carriers (NADH, $\\text{FADH}_2$), 2 ATP/GTP, and $\\text{CO}_2$.\n"
             "4. **Oxidative Phosphorylation & Electron Transport Chain (Inner Mitochondrial Membrane):** Electrons from NADH and $\\text{FADH}_2$ travel along protein complexes, pumping protons ($H^+$) into the intermembrane space to create an electrochemical gradient. Protons flow back through **ATP Synthase**, generating ~30–34 ATP."
    },
    {
        "q": "What are the defining characteristics of mammals?",
        "a": "**Mammals** (class *Mammalia*) are endothermic vertebrates defined by five primary biological characteristics:\n\n"
             "1. **Mammary Glands:** Females possess mammary glands that produce milk to nourish their newborn offspring.\n"
             "2. **Hair or Fur:** All mammals grow hair or fur at some point in their life cycle for insulation, sensory tactile input (whiskers), and camouflage.\n"
             "3. **Three Middle Ear Bones:** Mammals uniquely have three auditory ossicles - the **malleus (hammer)**, **incus (anvil)**, and **stapes (stirrup)** - derived evolutionarily from ancestral reptile jaw bones.\n"
             "4. **Neocortex:** A highly developed, layered region of the cerebral cortex responsible for higher-order sensory perception, conscious spatial reasoning, and motor commands.\n"
             "5. **Warm-Blooded (Endothermic):** Regulate constant internal body temperature metabolically independently of external ambient temperature."
    },
    {
        "q": "How do deep sea creatures survive extreme hydrostatic pressure and lack of sunlight?",
        "a": "Deep-sea organisms (in the bathypelagic, abyssopelagic, and hadal zones) thrive in extreme environments through remarkable biochemical and physiological adaptations:\n\n"
             "1. **Surviving Hydrostatic Pressure (>1,000 atmospheres):**\n"
             "   - **Piezolytes:** Cells contain high concentrations of organic osmolytes called *piezolytes* - most notably **TMAO (trimethylamine N-oxide)** - which physically bind water molecules and stabilize cellular proteins against pressure-induced unfolding.\n"
             "   - **Fluid Cell Membranes:** Cell membranes incorporate high concentrations of unsaturated fatty acids to maintain fluidity and prevent lipid phase crystallization.\n"
             "   - **Elimination of Gas Cavities:** Deep-sea fish lack gas-filled swim bladders and hollow air cavities that would implode under hydrostatic pressure.\n\n"
             "2. **Surviving Zero Sunlight:**\n"
             "   - **Chemosynthesis:** Ecosystems around hydrothermal vents rely on sulfur- and methane-oxidizing bacteria rather than photosynthesis for primary energy production.\n"
             "   - **Bioluminescence:** Luciferin-luciferase chemical reactions produce self-generated light used for predation, mate signaling, and counterillumination camouflage."
    },
    {
        "q": "What are the primary differences between bacteria and viruses?",
        "a": "**Key Differences Between Bacteria and Viruses:**\n\n"
             "1. **Biological Nature & Cellular Structure:**\n"
             "   - **Bacteria:** Living, single-celled, cellular prokaryotic microorganisms with a cell wall, cell membrane, cytoplasm, and independent metabolic machinery.\n"
             "   - **Viruses:** Non-living, acellular infectious particles consisting solely of genetic material (DNA or RNA) encased in a protein shell (capsid).\n\n"
             "2. **Reproduction:**\n"
             "   - **Bacteria:** Reproduce independently through asexual binary fission.\n"
             "   - **Viruses:** Cannot reproduce on their own; must invade a living host cell and hijack the host's cellular machinery to replicate.\n\n"
             "3. **Size:**\n"
             "   - **Bacteria:** Typically 1 to 5 micrometers (visible under light microscope).\n"
             "   - **Viruses:** Much smaller (20 to 400 nanometers; require electron microscope).\n\n"
             "4. **Treatment:**\n"
             "   - **Bacteria:** Treated with **antibiotics** (which target bacterial cell walls, ribosomes, or enzymes).\n"
             "   - **Viruses:** Unaffected by antibiotics; prevented by vaccines or managed with antiviral medications."
    },
    {
        "q": "Which bird is the only bird capable of flying backwards?",
        "a": "The **hummingbird** (family *Trochilidae*) is the only bird capable of sustained **flying backwards**, as well as flying upside down and hovering in mid-air with complete stationary control.\n\n"
             "- **Wing Mechanics:** While other birds flap their wings primarily up and down, hummingbirds rotate their wings in a continuous **figure-eight pattern** from specialized ball-and-socket shoulder joints.\n"
             "- **Aerodynamic Lift:** They generate lift on both the downstroke and upstroke (75% on downstroke, 25% on upstroke), operating aerodynamically similar to helicopter rotors or insect flight."
    },
    {
        "q": "Explain Darwin's theory of natural selection and survival of the fittest.",
        "a": "Charles Darwin's **Theory of Evolution by Natural Selection** is the foundational mechanism explaining how biological species adapt and diversify over generations:\n\n"
             "1. **Phenotypic Variation:** Individuals within any natural population exhibit genetic variations in morphology, physiology, and behavior.\n"
             "2. **Overproduction & Struggle for Existence:** Organisms produce more offspring than environmental carrying capacity can support, leading to competition for limited food, territory, and mates.\n"
             "3. **Differential Survival & Reproduction:** Individuals possessing heritable traits and adaptations better suited to their environment enjoy higher survival rates and **greater reproductive success** (the true biological definition of 'fitness').\n"
             "4. **Gradual Adaptation:** Over successive generations, favorable alleles and traits accumulate in the gene pool, driving evolutionary change and speciation."
    },
    {
        "q": "How do neurons transmit electrical signals through action potentials?",
        "a": "Neurons transmit electrical signals along their axons via **action potentials** - rapid, all-or-nothing electrical impulses driven by voltage-gated ion channels across the cell membrane:\n\n"
             "1. **Resting Membrane Potential (~ -70 mV):** Maintained by the $Na^+/K^+$ ATPase pump (pumps 3 $Na^+$ out for every 2 $K^+$ in), creating a polarized membrane with higher extracellular sodium and higher intracellular potassium.\n"
             "2. **Threshold & Depolarization:** When dendritic stimulation reaches the threshold potential (~ -55 mV), **voltage-gated Sodium ($Na^+$) channels** snap open. Positively charged $Na^+$ rushes into the axon, rapidly depolarizing the membrane up to approximately **+30 mV**.\n"
             "3. **Repolarization:** Sodium channels inactivate, and **voltage-gated Potassium ($K^+$) channels** open. $K^+$ flows rapidly out of the cell, restoring negative internal potential.\n"
             "4. **Hyperpolarization & Refractory Period:** The membrane briefly overshoots below -70 mV before returning to resting state. This absolute refractory period ensures unidirectional signal propagation along the axon to the synaptic terminal."
    },
    {
        "q": "How do migratory birds navigate over thousands of miles during migration?",
        "a": "**Migratory birds** navigate across continents using a sophisticated multi-sensor biological navigation suite:\n\n"
             "1. **Geomagnetic Compass (Magnetoreception):** Birds detect Earth's geomagnetic field lines using light-sensitive **cryptochrome** proteins in their retinal eye cells (quantum radical-pair mechanism) and magnetite mineral clusters in their beaks, allowing them to perceive both direction and magnetic inclination.\n"
             "2. **Celestial / Star Navigation:** Nocturnal migrants orient themselves using star patterns and constellations rotating around the celestial pole (e.g., Polaris in the Northern Hemisphere).\n"
             "3. **Sun Compass & Circadian Clock:** Diurnal migrants determine flight headings by tracking the Sun's azimuth combined with an internal circadian biological clock to compensate for solar movement.\n"
             "4. **Olfactory & Infrasound Maps:** Birds utilize low-frequency atmospheric sound waves and regional olfactory scent maps to identify coastlines, mountain ranges, and specific nesting sites."
    },
    {
        "q": "How many hearts does an octopus have and what color is its blood?",
        "a": "An octopus has **three hearts** and **blue blood**:\n\n"
             "- **Three Hearts:**\n"
             "  1. **Two Branchial Hearts:** Positioned at the base of each gill, these pump deoxygenated blood through the gills to absorb oxygen.\n"
             "  2. **One Systemic Heart:** The central heart pumps oxygenated blood from the gills through the rest of the body. (The systemic heart stops beating when the octopus swims, which is why they prefer crawling along the seafloor to conserve energy).\n\n"
             "- **Blue Blood:**\n"
             "  Octopus blood is blue because it uses **hemocyanin** - a copper-rich protein - to transport oxygen, rather than iron-based hemoglobin. Hemocyanin is significantly more efficient at transporting oxygen in cold, low-oxygen marine environments."
    },

    # --- Geography & World Knowledge ---
    {
        "q": "How many sovereign countries are in the world today according to the United Nations?",
        "a": "According to the United Nations, there are **195 recognized sovereign countries** in the world today:\n\n"
             "- **193 UN Member States**\n"
             "- **2 Permanent UN Non-Member Observer States**:\n"
             "  1. **Vatican City** (Holy See)\n"
             "  2. **State of Palestine**"
    },
    {
        "q": "What is the longest river in the world?",
        "a": "The **Nile River** is traditionally recognized as the longest river in the world.\n\n"
             "- **Length:** Approximately **6,650 kilometers** (**4,132 miles**).\n"
             "- **Geography:** Located in northeastern Africa, flowing northward through 11 countries (including Egypt, Sudan, South Sudan, Ethiopia, Uganda, Kenya, Tanzania, Rwanda, Burundi, DR Congo, and Eritrea) before emptying into the Mediterranean Sea.\n"
             "- Note: While the Amazon River is the world's largest river by water discharge volume, the Nile holds the official geographic record for total length."
    },
    {
        "q": "What is the highest mountain peak above sea level on Earth?",
        "a": "**Mount Everest** (known as *Sagarmatha* in Nepal and *Chomolungma* in Tibet) is the highest mountain peak above sea level on Earth.\n\n"
             "- **Elevation:** **8,848.86 meters** (**29,031.7 feet**) above sea level.\n"
             "- **Location:** Mahalangur Himal sub-range of the Himalayas, straddling the international border between Nepal and China (Tibet Autonomous Region)."
    },
    {
        "q": "What is the deepest point in the world's oceans?",
        "a": "The **Challenger Deep** in the **Mariana Trench** is the deepest known point in the world's oceans.\n\n"
             "- **Depth:** Approximately **10,994 meters** (**36,070 feet** / ~6.8 miles) below sea level.\n"
             "- **Location:** Western Pacific Ocean, roughly 300 kilometers southwest of Guam.\n"
             "- **Pressure:** Extreme hydrostatic pressure of over 1,086 bar (15,750 psi) - more than 1,000 times atmospheric pressure at sea level."
    },
    {
        "q": "Which country has the longest coastline in the world?",
        "a": "**Canada** has the longest coastline in the world by a wide margin.\n\n"
             "- **Coastline Length:** Approximately **202,080 kilometers** (**125,567 miles**).\n"
             "- **Oceans:** Spans across three oceans - the Atlantic Ocean to the east, Pacific Ocean to the west, and Arctic Ocean to the north, including more than 52,000 islands within the Canadian Arctic Archipelago."
    },
    {
        "q": "What is the official currency of the United Kingdom?",
        "a": "The official currency of the United Kingdom is the **Pound Sterling** (**GBP**), represented by the currency symbol **£**.\n\n"
             "- Often simply referred to as the **British pound** or **sterling**.\n"
             "- It is subdivided into 100 pence (symbol: p).\n"
             "- It is the oldest currency in continuous use in the world."
    },
    {
        "q": "Where is the Amazon Rainforest located and which countries does it span?",
        "a": "The **Amazon Rainforest** is located in **South America** within the Amazon River drainage basin.\n\n"
             "It encompasses over 5.5 million square kilometers across **9 South American nations**:\n"
             "1. **Brazil** (~60% of the forest)\n"
             "2. **Peru** (~13%)\n"
             "3. **Colombia** (~10%)\n"
             "4. **Venezuela**\n"
             "5. **Ecuador**\n"
             "6. **Bolivia**\n"
             "7. **Guyana**\n"
             "8. **Suriname**\n"
             "9. **French Guiana** (overseas department of France)"
    },
    {
        "q": "Which transcontinental country connects Europe and Asia across the Bosphorus Strait?",
        "a": "**Turkey** (**Türkiye**) is the transcontinental country that connects Europe and Asia across the **Bosphorus Strait**.\n\n"
             "- **Bosphorus Strait:** Connects the Black Sea to the Sea of Marmara, forming the geographic continental boundary between southeastern Europe (Thrace) and southwestern Asia (Anatolia).\n"
             "- **Istanbul:** The country's historic commercial hub and largest city, famously straddling both the European and Asian continents."
    },

    # --- Computer Science Concepts ---
    {
        "q": "Explain how a Binary Search Tree (BST) works, including its search, insert, and delete operations and average vs worst-case time complexity.",
        "a": "A **Binary Search Tree (BST)** is a hierarchical binary tree data structure where each node contains a key/value satisfying the **BST ordering property**:\n"
             "- The **left subtree** of a node contains only keys strictly less than the node's key ($<$).\n"
             "- The **right subtree** of a node contains only keys strictly greater than the node's key ($>$).\n\n"
             "**Core Operations:**\n"
             "1. **Search:** Compares the target with the current node; recursively descends left if smaller, right if larger, or terminates on match.\n"
             "2. **Insert:** Traverses the tree like search until finding a null child pointer, attaching the new leaf node in its correct sorted position.\n"
             "3. **Delete:**\n"
             "   - Node with 0 children (leaf): remove directly.\n"
             "   - Node with 1 child: bypass node, linking parent directly to child.\n"
             "   - Node with 2 children: replace node with its in-order successor (minimum node of right subtree) or in-order predecessor, then delete that successor.\n\n"
             "**Time Complexity Analysis:**\n"
             "- **Average Case (Balanced):** $O(\\log n)$ for search, insert, and delete because tree height $h \\approx \\log_2 n$.\n"
             "- **Worst Case (Degenerate):** $O(n)$ if items are inserted in sorted order, collapsing into a linear linked list."
    },
    {
        "q": "Explain the difference between Quick Sort and Merge Sort. Which one is stable and what are their worst-case time complexities?",
        "a": "**Quick Sort vs. Merge Sort Comparison:**\n\n"
             "1. **Stability:**\n"
             "   - **Merge Sort is STABLE:** Preserves the relative order of duplicate elements.\n"
             "   - **Quick Sort is UNSTABLE:** Standard in-place partitioning can swap equal elements past each other.\n\n"
             "2. **Worst-Case Time Complexity:**\n"
             "   - **Merge Sort:** Guaranteed **$O(n \\log n)$** time in all cases (worst, best, average).\n"
             "   - **Quick Sort:** **$O(n^2)$** worst-case time (occurs when bad pivot selection results in maximally unbalanced partitions, such as already sorted arrays with first/last element pivot); average time is $O(n \\log n)$.\n\n"
             "3. **Space Complexity & Memory:**\n"
             "   - **Merge Sort:** $O(n)$ auxiliary space to merge subarrays.\n"
             "   - **Quick Sort:** $O(\\log n)$ space for the recursive call stack (in-place sorting)."
    },
    {
        "q": "Explain the difference between asynchronous programming, multithreading, and multiprocessing in Python.",
        "a": "**Asynchronous vs. Multithreading vs. Multiprocessing in Python:**\n\n"
             "1. **Asynchronous Programming (`asyncio`):**\n"
             "   - **Model:** Single thread, single process running a cooperative **event loop** with non-blocking coroutines (`async`/`await`).\n"
             "   - **Best For:** Massive I/O-bound concurrency (thousands of simultaneous web sockets, HTTP requests, database queries).\n"
             "   - **GIL Impact:** Unaffected by the GIL because it executes cooperatively in one thread without preemption.\n\n"
             "2. **Multithreading (`threading`):**\n"
             "   - **Model:** Multiple operating system threads sharing the same process memory space.\n"
             "   - **Best For:** I/O-bound operations (file I/O, network calls) where threads sleep waiting for external I/O.\n"
             "   - **GIL Impact:** Constrained by CPython's **Global Interpreter Lock (GIL)**: only one thread executes Python bytecode at any given moment, preventing parallel CPU execution.\n\n"
             "3. **Multiprocessing (`multiprocessing`):**\n"
             "   - **Model:** Spawns separate OS processes, each with its own independent memory address space and independent GIL instance.\n"
             "   - **Best For:** CPU-bound tasks (image processing, machine learning, heavy numerical computation).\n"
             "   - **Tradeoff:** True multi-core parallel computation, but higher memory footprint and inter-process communication (IPC) overhead."
    },
    {
        "q": "Explain how RSA asymmetric cryptography works, including public and private key generation and modular exponentiation.",
        "a": "**RSA (Rivest-Shamir-Adleman)** is an asymmetric public-key cryptosystem based on the computational difficulty of factoring the product of two large prime numbers:\n\n"
             "**1. Key Generation:**\n"
             "1. Choose two distinct, large random prime numbers $p$ and $q$.\n"
             "2. Compute the modulus $n = p \\times q$.\n"
             "3. Calculate Euler's totient function: $\\phi(n) = (p - 1)(q - 1)$.\n"
             "4. Select an integer public exponent $e$ such that $1 < e < \\phi(n)$ and $\\gcd(e, \\phi(n)) = 1$ (commonly $e = 65537$).\n"
             "5. Compute private exponent $d$ as the modular multiplicative inverse of $e \\pmod{\\phi(n)}$: $d \\cdot e \\equiv 1 \\pmod{\\phi(n)}$.\n"
             "- **Public Key:** $(e, n)$\n"
             "- **Private Key:** $(d, n)$\n\n"
             "**2. Encryption & Decryption (Modular Exponentiation):**\n"
             "- **Encryption:** Convert plaintext message $M$ ($M < n$) into ciphertext $C$: $C \\equiv M^e \\pmod n$.\n"
             "- **Decryption:** Recover original message using private key $d$: $M \\equiv C^d \\pmod n$.\n"
             "By Euler's Totient Theorem, $(M^e)^d = M^{ed} = M^{k \\phi(n) + 1} \\equiv M \\pmod n$."
    }
]


def seed():
    mem = Memory()
    embedder = Embedder()
    print(f"Seeding {len(ENTRIES)} authoritative multi-domain entries...")
    added = 0
    for item in ENTRIES:
        q = item["q"]
        ans = item["a"]
        evidence = [{"url": "learned://authoritative", "title": "TenSeiAi Verified Knowledge"}]
        qemb = embedder.encode(q)
        emb0 = embedder.base_encode(q)
        mem.conn.execute("DELETE FROM qa WHERE question = ?", (q,))
        mem.add_qa(q, ans, evidence, qemb, emb0=emb0)
        added += 1

    mem.conn.commit()
    # Invalidate cache
    mem._qa_base_cache = None
    print(f"Successfully updated/inserted {added} knowledge entries!")


if __name__ == "__main__":
    seed()
