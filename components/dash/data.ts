// Mock data approximating Stortinget API shape.
// Seat counts reflect 2025-2029 perioden (approximate for mock).

export type Side = "left" | "right" | "center";

export type Party = {
  id: string;
  name: string;
  short: string;
  color: string;
  seats: number;
  leader: string;
  side: Side;
  position: { econ: number; social: number };
};

export type Committee = {
  id: string;
  name: string;
  short: string;
  members: number;
  chair: string;
};

export type Representative = {
  id: string;
  name: string;
  party: string;
  fylke: string;
  born: number;
  committee: string;
  role: string;
  voteShare: number;
};

export type Bill = {
  id: string;
  title: string;
  kortTitle: string;
  category: string;
  committee: string;
  status: "Til behandling" | "Vedtatt" | "Avvist" | "Trukket";
  stage: 1 | 2 | 3 | 4;
  proposer: string;
  proposerParty: string;
  date: string;
  debates: number;
  amendments: number;
  aiSummary: string;
  aiKeyPoints: string[];
  expectedSupport: { for: string[]; against: string[]; split: string[] };
  outcome?: { for: number; against: number; absent: number };
};

export type PartyVoteCounts = { for: number; against: number; absent: number; total: number };

export type Vote = {
  id: string;
  bill: string;
  title: string;
  date: string;
  time: string;
  result: "vedtatt" | "avvist";
  tally: { for: number; against: number; absent: number };
  by: Record<string, PartyVoteCounts>;
};

export const PARTIES: Party[] = [
  { id: "A",   name: "Arbeiderpartiet",           short: "Ap",  color: "var(--ap)",  seats: 53, leader: "Jonas Gahr Støre",        side: "left",   position: { econ: -0.4, social: 0.2 } },
  { id: "H",   name: "Høyre",                     short: "H",   color: "var(--h)",   seats: 36, leader: "Erna Solberg",             side: "right",  position: { econ:  0.6, social: 0.1 } },
  { id: "FrP", name: "Fremskrittspartiet",        short: "FrP", color: "var(--frp)", seats: 21, leader: "Sylvi Listhaug",           side: "right",  position: { econ:  0.8, social: -0.5 } },
  { id: "Sp",  name: "Senterpartiet",             short: "Sp",  color: "var(--sp)",  seats: 28, leader: "Trygve Slagsvold Vedum",   side: "center", position: { econ: -0.1, social: -0.3 } },
  { id: "SV",  name: "Sosialistisk Venstreparti", short: "SV",  color: "var(--sv)",  seats: 13, leader: "Kirsti Bergstø",           side: "left",   position: { econ: -0.7, social: 0.6 } },
  { id: "R",   name: "Rødt",                      short: "R",   color: "var(--r)",   seats:  8, leader: "Marie Sneve Martinussen",  side: "left",   position: { econ: -0.9, social: 0.7 } },
  { id: "V",   name: "Venstre",                   short: "V",   color: "var(--v)",   seats:  8, leader: "Guri Melby",               side: "center", position: { econ:  0.3, social: 0.5 } },
  { id: "KrF", name: "Kristelig Folkeparti",      short: "KrF", color: "var(--krf)", seats:  3, leader: "Dag Inge Ulstein",         side: "center", position: { econ:  0.1, social: -0.6 } },
  { id: "MDG", name: "Miljøpartiet De Grønne",    short: "MDG", color: "var(--mdg)", seats:  3, leader: "Arild Hermstad",           side: "left",   position: { econ: -0.3, social: 0.7 } },
  { id: "PF",  name: "Pasientfokus",              short: "PF",  color: "var(--pf)",  seats:  1, leader: "Irene Ojala",              side: "center", position: { econ: -0.1, social: 0.0 } },
];

export const COMMITTEES: Committee[] = [
  { id: "arbeid",    name: "Arbeids- og sosialkomiteen",           short: "AS",  members: 15, chair: "Kari Henriksen" },
  { id: "energi",    name: "Energi- og miljøkomiteen",             short: "EM",  members: 17, chair: "Marianne Sivertsen Næss" },
  { id: "familie",   name: "Familie- og kulturkomiteen",           short: "FK",  members: 13, chair: "Grunde Almeland" },
  { id: "finans",    name: "Finanskomiteen",                       short: "FIN", members: 19, chair: "Eigil Knutsen" },
  { id: "forsvar",   name: "Utenriks- og forsvarskomiteen",        short: "UFK", members: 17, chair: "Ine Eriksen Søreide" },
  { id: "helse",     name: "Helse- og omsorgskomiteen",            short: "HO",  members: 15, chair: "Tone Wilhelmsen Trøen" },
  { id: "justis",    name: "Justiskomiteen",                       short: "JUS", members: 11, chair: "Per-Willy Amundsen" },
  { id: "kommunal",  name: "Kommunal- og forvaltningskomiteen",    short: "KFK", members: 15, chair: "Siri Gåsemyr Staalesen" },
  { id: "kontroll",  name: "Kontroll- og konstitusjonskomiteen",   short: "KKK", members: 13, chair: "Peter Frølich" },
  { id: "naering",   name: "Næringskomiteen",                      short: "NÆR", members: 13, chair: "Willfred Nordlund" },
  { id: "transport", name: "Transport- og kommunikasjonskomiteen", short: "TK",  members: 15, chair: "Morten Stordalen" },
  { id: "utdanning", name: "Utdannings- og forskningskomiteen",    short: "UF",  members: 13, chair: "Freddy André Øvstegård" },
];

export const REPRESENTATIVES: Representative[] = [
  { id: "JGS",  name: "Jonas Gahr Støre",         party: "A",   fylke: "Oslo",            born: 1960, committee: "forsvar",   role: "Statsminister",        voteShare: 0.97 },
  { id: "ES",   name: "Erna Solberg",             party: "H",   fylke: "Hordaland",       born: 1961, committee: "finans",    role: "Parlamentarisk leder", voteShare: 0.96 },
  { id: "SL",   name: "Sylvi Listhaug",           party: "FrP", fylke: "Møre og Romsdal", born: 1977, committee: "finans",    role: "Parlamentarisk leder", voteShare: 0.94 },
  { id: "TSV",  name: "Trygve Slagsvold Vedum",   party: "Sp",  fylke: "Hedmark",         born: 1978, committee: "finans",    role: "Finansminister",       voteShare: 0.92 },
  { id: "KB",   name: "Kirsti Bergstø",           party: "SV",  fylke: "Akershus",        born: 1981, committee: "arbeid",    role: "Parlamentarisk leder", voteShare: 0.95 },
  { id: "MSM",  name: "Marie Sneve Martinussen",  party: "R",   fylke: "Akershus",        born: 1985, committee: "finans",    role: "Parlamentarisk leder", voteShare: 0.93 },
  { id: "GM",   name: "Guri Melby",               party: "V",   fylke: "Oslo",            born: 1981, committee: "utdanning", role: "Parlamentarisk leder", voteShare: 0.91 },
  { id: "DIU",  name: "Dag Inge Ulstein",         party: "KrF", fylke: "Hordaland",       born: 1980, committee: "kommunal",  role: "Parlamentarisk leder", voteShare: 0.89 },
  { id: "AH",   name: "Arild Hermstad",           party: "MDG", fylke: "Hordaland",       born: 1965, committee: "energi",    role: "Parlamentarisk leder", voteShare: 0.88 },
  { id: "IES",  name: "Ine Eriksen Søreide",      party: "H",   fylke: "Oslo",            born: 1976, committee: "forsvar",   role: "Komitéleder",          voteShare: 0.90 },
  { id: "PWA",  name: "Per-Willy Amundsen",       party: "FrP", fylke: "Troms",           born: 1971, committee: "justis",    role: "Komitéleder",          voteShare: 0.87 },
  { id: "KH",   name: "Kari Henriksen",           party: "A",   fylke: "Vest-Agder",      born: 1955, committee: "arbeid",    role: "Komitéleder",          voteShare: 0.93 },
  { id: "EK",   name: "Eigil Knutsen",            party: "A",   fylke: "Hordaland",       born: 1987, committee: "finans",    role: "Komitéleder",          voteShare: 0.96 },
  { id: "TWT",  name: "Tone Wilhelmsen Trøen",    party: "H",   fylke: "Akershus",        born: 1966, committee: "helse",     role: "Komitéleder",          voteShare: 0.92 },
  { id: "PF",   name: "Peter Frølich",            party: "H",   fylke: "Hordaland",       born: 1987, committee: "kontroll",  role: "Komitéleder",          voteShare: 0.88 },
  { id: "GA",   name: "Grunde Almeland",          party: "V",   fylke: "Oslo",            born: 1991, committee: "familie",   role: "Komitéleder",          voteShare: 0.85 },
  { id: "MSN",  name: "Marianne Sivertsen Næss",  party: "A",   fylke: "Finnmark",        born: 1973, committee: "energi",    role: "Komitéleder",          voteShare: 0.91 },
  { id: "WN",   name: "Willfred Nordlund",        party: "Sp",  fylke: "Nordland",        born: 1985, committee: "naering",   role: "Komitéleder",          voteShare: 0.90 },
  { id: "MS",   name: "Morten Stordalen",         party: "FrP", fylke: "Vestfold",        born: 1964, committee: "transport", role: "Komitéleder",          voteShare: 0.86 },
  { id: "FAØ",  name: "Freddy André Øvstegård",   party: "SV",  fylke: "Østfold",         born: 1994, committee: "utdanning", role: "Komitéleder",          voteShare: 0.89 },
  { id: "SGS",  name: "Siri Gåsemyr Staalesen",   party: "A",   fylke: "Oslo",            born: 1977, committee: "kommunal",  role: "Komitéleder",          voteShare: 0.94 },
  { id: "IO",   name: "Irene Ojala",              party: "PF",  fylke: "Finnmark",        born: 1962, committee: "helse",     role: "Representant",         voteShare: 0.82 },
  { id: "HES",  name: "Hadia Tajik",              party: "A",   fylke: "Rogaland",        born: 1983, committee: "finans",    role: "Representant",         voteShare: 0.92 },
  { id: "NT",   name: "Nikolai Astrup",           party: "H",   fylke: "Oslo",            born: 1978, committee: "energi",    role: "Representant",         voteShare: 0.89 },
  { id: "LB",   name: "Lan Marie Berg",           party: "MDG", fylke: "Oslo",            born: 1987, committee: "energi",    role: "Representant",         voteShare: 0.90 },
  { id: "TK",   name: "Torbjørn Røe Isaksen",     party: "H",   fylke: "Telemark",        born: 1978, committee: "naering",   role: "Representant",         voteShare: 0.84 },
  { id: "MSK",  name: "Mona Fagerås",             party: "SV",  fylke: "Nordland",        born: 1966, committee: "utdanning", role: "Representant",         voteShare: 0.91 },
  { id: "AV",   name: "Abid Raja",                party: "V",   fylke: "Akershus",        born: 1975, committee: "justis",    role: "Representant",         voteShare: 0.83 },
  { id: "HB",   name: "Hege Bae Nyholt",          party: "R",   fylke: "Sør-Trøndelag",   born: 1977, committee: "utdanning", role: "Representant",         voteShare: 0.88 },
  { id: "BS",   name: "Bård Ludvig Thorheim",     party: "H",   fylke: "Nordland",        born: 1983, committee: "forsvar",   role: "Representant",         voteShare: 0.87 },
];

export const BILLS: Bill[] = [
  {
    id: "Prop. 142 L (2025–2026)",
    title: "Endringer i skatteloven — justering av formuesskatt på arbeidende kapital",
    kortTitle: "Formuesskatt på arbeidende kapital",
    category: "Skatt og avgift",
    committee: "finans",
    status: "Til behandling",
    stage: 3,
    proposer: "Regjeringen",
    proposerParty: "A",
    date: "2026-04-02",
    debates: 4,
    amendments: 11,
    aiSummary:
      "Regjeringen foreslår å redusere verdsettelsen av arbeidende kapital fra 80 % til 70 % med virkning fra inntektsåret 2027. Hensikten er å stimulere investeringer i norske bedrifter. Opposisjonen fra Høyre og FrP ønsker full bortfall; SV og Rødt går imot enhver reduksjon. Anslått provenyeffekt: −1,8 mrd. kr.",
    aiKeyPoints: [
      "Redusert verdsettelse 80 → 70 %",
      "Virkning fra inntektsåret 2027",
      "Anslått provenytap: 1,8 mrd. kr",
      "Dissens fra SV, R, MDG i komité",
    ],
    expectedSupport: { for: ["A", "Sp", "V", "KrF"], against: ["SV", "R", "MDG"], split: ["H", "FrP"] },
  },
  {
    id: "Prop. 138 S (2025–2026)",
    title: "Oppfølging av klimaplan 2030 — forsterkede tiltak i transportsektoren",
    kortTitle: "Klimaplan transport 2030",
    category: "Klima og miljø",
    committee: "energi",
    status: "Til behandling",
    stage: 2,
    proposer: "Regjeringen",
    proposerParty: "A",
    date: "2026-03-28",
    debates: 2,
    amendments: 23,
    aiSummary:
      "Proposisjonen foreslår innskjerping av CO₂-avgift på drivstoff, utvidet støtteordning for tungtransport, og nye krav til ladeinfrastruktur langs riksveinettet. MDG og SV krever større kutt; FrP vil reversere deler av dagens avgift. Komiteen er dypt splittet.",
    aiKeyPoints: [
      "Økning i CO₂-avgift på 10 %",
      "3 mrd. kr til ladeinfrastruktur",
      "Nullutslippskrav for nye tungtransportkjøretøy 2030",
      "Fritak for distriktene under vurdering",
    ],
    expectedSupport: { for: ["A", "Sp", "SV", "MDG", "V"], against: ["FrP"], split: ["H", "R", "KrF"] },
  },
  {
    id: "Innst. 221 S (2025–2026)",
    title: "Representantforslag om nasjonal strategi for kunstig intelligens i offentlig sektor",
    kortTitle: "Nasjonal AI-strategi",
    category: "Digitalisering",
    committee: "kommunal",
    status: "Vedtatt",
    stage: 4,
    proposer: "V, H, KrF",
    proposerParty: "V",
    date: "2026-03-15",
    debates: 3,
    amendments: 7,
    aiSummary:
      "Forslag om å be regjeringen legge frem en nasjonal strategi for bruk av kunstig intelligens i offentlig sektor innen 1. januar 2027. Enstemmig vedtatt med mindre endringer. Strategien skal omfatte personvern, etikk og kompetansebygging.",
    aiKeyPoints: [
      "Strategi skal leveres 01.01.2027",
      "Personvern og etikk sentralt",
      "Enstemmig vedtatt",
      "500 mill. kr øremerket 2027",
    ],
    expectedSupport: { for: ["A", "H", "Sp", "FrP", "SV", "R", "V", "KrF", "MDG"], against: [], split: [] },
    outcome: { for: 168, against: 0, absent: 1 },
  },
  {
    id: "Prop. 131 L (2025–2026)",
    title: "Endringer i helse- og omsorgstjenesteloven — innføring av fastlegegaranti",
    kortTitle: "Fastlegegaranti",
    category: "Helse",
    committee: "helse",
    status: "Til behandling",
    stage: 3,
    proposer: "Regjeringen",
    proposerParty: "A",
    date: "2026-03-10",
    debates: 5,
    amendments: 18,
    aiSummary:
      "Lovforslag om å gi alle innbyggere rett til fastlege innen 30 dager. Krever stor budsjettutvidelse (est. 2,4 mrd. kr) og rekruttering av 400 nye fastleger. Støttes bredt, men uenighet om finansiering.",
    aiKeyPoints: [
      "Rett til fastlege innen 30 dager",
      "400 nye stillinger over 3 år",
      "Kostnad: 2,4 mrd. kr",
      "Uenighet om kommunal vs. statlig finansiering",
    ],
    expectedSupport: { for: ["A", "Sp", "SV", "R", "MDG", "KrF"], against: [], split: ["H", "FrP", "V"] },
  },
  {
    id: "Dok. 8:154 S (2025–2026)",
    title: "Forslag om styrket vern av villrein i Nordfjella og Hardangervidda",
    kortTitle: "Villrein — utvidet vern",
    category: "Klima og miljø",
    committee: "energi",
    status: "Avvist",
    stage: 4,
    proposer: "MDG, SV, R",
    proposerParty: "MDG",
    date: "2026-02-28",
    debates: 2,
    amendments: 4,
    aiSummary:
      "Representantforslag om å utvide verneområdet og redusere hyttebygging i randsonen. Regjeringspartiet og Sp gikk mot; viste til pågående forvaltningsplan. Avvist med 122 mot 47 stemmer.",
    aiKeyPoints: [
      "Utvidelse av verneareal 12 %",
      "Byggeforbud i randsone",
      "Avvist 122–47",
      "Pågående forvaltningsplan angitt som årsak",
    ],
    expectedSupport: { for: ["SV", "R", "MDG", "V"], against: ["A", "Sp", "FrP", "KrF"], split: ["H"] },
    outcome: { for: 47, against: 122, absent: 0 },
  },
  {
    id: "Prop. 119 L (2025–2026)",
    title: "Endringer i utlendingsloven — innstramming i familiegjenforening",
    kortTitle: "Utlendingsloven — familiegjenforening",
    category: "Innvandring",
    committee: "kommunal",
    status: "Til behandling",
    stage: 2,
    proposer: "Regjeringen",
    proposerParty: "A",
    date: "2026-02-20",
    debates: 3,
    amendments: 15,
    aiSummary:
      "Forslag om økte inntektskrav og lengre ventetid for familiegjenforening for flyktninger. Støttes av FrP og H, avvises av SV, R, MDG, V og KrF. Splittelse innad i Ap.",
    aiKeyPoints: [
      "Inntektskrav økes til 350 000 kr/år",
      "Ventetid: fra 2 til 4 år",
      "Intern Ap-dissens signalisert",
      "4 høringsinstanser sterkt kritiske",
    ],
    expectedSupport: { for: ["FrP", "H"], against: ["SV", "R", "MDG", "V", "KrF"], split: ["A", "Sp"] },
  },
  {
    id: "Innst. 198 S (2025–2026)",
    title: "Representantforslag om økt minstepensjon og samordning med grunnpensjon",
    kortTitle: "Økt minstepensjon",
    category: "Trygd og pensjon",
    committee: "arbeid",
    status: "Til behandling",
    stage: 3,
    proposer: "R, SV",
    proposerParty: "R",
    date: "2026-02-15",
    debates: 2,
    amendments: 3,
    aiSummary:
      "Forslag om å heve minstepensjonen med 12 000 kr/år og reformere samordningsreglene. Regjeringen viser til pågående pensjonsreform-behandling; opposisjon til venstre støtter. Ventet flertall mot.",
    aiKeyPoints: [
      "Økning: 12 000 kr/år",
      "Kostnad: 3,1 mrd. kr",
      "Mot: A, H, Sp, FrP",
      "Pensjonsreform pågår parallelt",
    ],
    expectedSupport: { for: ["SV", "R", "MDG"], against: ["A", "H", "FrP", "Sp"], split: ["V", "KrF"] },
  },
  {
    id: "Prop. 99 L (2025–2026)",
    title: "Endringer i barnevernsloven — styrking av ettervern",
    kortTitle: "Barnevern — ettervern til 25 år",
    category: "Familie",
    committee: "familie",
    status: "Vedtatt",
    stage: 4,
    proposer: "Regjeringen",
    proposerParty: "A",
    date: "2026-01-25",
    debates: 4,
    amendments: 9,
    aiSummary:
      "Utvidelse av ettervern i barnevern fra 23 til 25 år, med rett til bolig- og utdanningsstøtte. Vedtatt 165–4 med bred støtte.",
    aiKeyPoints: [
      "Ettervern utvides til 25 år",
      "Rett til boligstøtte",
      "Kostnad: 680 mill. kr/år",
      "Vedtatt 165–4",
    ],
    expectedSupport: { for: ["A", "H", "Sp", "SV", "R", "V", "KrF", "MDG"], against: ["FrP"], split: [] },
    outcome: { for: 165, against: 4, absent: 0 },
  },
];

export const RECENT_VOTES: Vote[] = [
  {
    id: "V-2026-04-15-AI",
    bill: "Innst. 221 S (2025–2026)",
    title: "Nasjonal strategi for kunstig intelligens",
    date: "2026-04-15",
    time: "14:23",
    result: "vedtatt",
    tally: { for: 168, against: 0, absent: 1 },
    by: {
      A:   { for: 53, against: 0, absent: 0, total: 53 },
      H:   { for: 36, against: 0, absent: 0, total: 36 },
      FrP: { for: 21, against: 0, absent: 0, total: 21 },
      Sp:  { for: 27, against: 0, absent: 1, total: 28 },
      SV:  { for: 13, against: 0, absent: 0, total: 13 },
      R:   { for:  8, against: 0, absent: 0, total:  8 },
      V:   { for:  8, against: 0, absent: 0, total:  8 },
      KrF: { for:  3, against: 0, absent: 0, total:  3 },
      MDG: { for:  3, against: 0, absent: 0, total:  3 },
      PF:  { for:  1, against: 0, absent: 0, total:  1 },
    },
  },
  {
    id: "V-2026-04-10-VIL",
    bill: "Dok. 8:154 S (2025–2026)",
    title: "Utvidet vern av villrein",
    date: "2026-04-10",
    time: "13:47",
    result: "avvist",
    tally: { for: 47, against: 122, absent: 0 },
    by: {
      A:   { for:  0, against: 53, absent: 0, total: 53 },
      H:   { for:  2, against: 34, absent: 0, total: 36 },
      FrP: { for:  0, against: 21, absent: 0, total: 21 },
      Sp:  { for:  0, against: 28, absent: 0, total: 28 },
      SV:  { for: 13, against:  0, absent: 0, total: 13 },
      R:   { for:  8, against:  0, absent: 0, total:  8 },
      V:   { for:  8, against:  0, absent: 0, total:  8 },
      KrF: { for:  0, against:  3, absent: 0, total:  3 },
      MDG: { for:  3, against:  0, absent: 0, total:  3 },
      PF:  { for:  1, against:  0, absent: 0, total:  1 },
    },
  },
  {
    id: "V-2026-04-03-BV",
    bill: "Prop. 99 L (2025–2026)",
    title: "Ettervern barnevern til 25 år",
    date: "2026-04-03",
    time: "11:15",
    result: "vedtatt",
    tally: { for: 165, against: 4, absent: 0 },
    by: {
      A:   { for: 53, against:  0, absent: 0, total: 53 },
      H:   { for: 36, against:  0, absent: 0, total: 36 },
      FrP: { for: 17, against:  4, absent: 0, total: 21 },
      Sp:  { for: 28, against:  0, absent: 0, total: 28 },
      SV:  { for: 13, against:  0, absent: 0, total: 13 },
      R:   { for:  8, against:  0, absent: 0, total:  8 },
      V:   { for:  8, against:  0, absent: 0, total:  8 },
      KrF: { for:  3, against:  0, absent: 0, total:  3 },
      MDG: { for:  3, against:  0, absent: 0, total:  3 },
      PF:  { for:  1, against:  0, absent: 0, total:  1 },
    },
  },
];

export const AGREEMENT_SERIES: Record<string, number[]> = {
  A:   [1.00,1.00,0.98,1.00,0.99,0.97,1.00,0.99,0.98,1.00,0.99,1.00,0.99],
  Sp:  [0.96,0.95,0.97,0.94,0.96,0.93,0.95,0.94,0.92,0.94,0.93,0.95,0.94],
  SV:  [0.74,0.72,0.78,0.71,0.69,0.74,0.73,0.68,0.72,0.75,0.71,0.74,0.70],
  R:   [0.58,0.55,0.62,0.56,0.54,0.59,0.55,0.52,0.58,0.61,0.55,0.58,0.57],
  MDG: [0.68,0.65,0.70,0.67,0.64,0.71,0.69,0.65,0.68,0.72,0.68,0.70,0.67],
  V:   [0.48,0.52,0.50,0.54,0.51,0.55,0.52,0.58,0.54,0.53,0.56,0.54,0.57],
  KrF: [0.44,0.47,0.45,0.50,0.48,0.46,0.49,0.52,0.48,0.50,0.49,0.51,0.48],
  H:   [0.32,0.35,0.30,0.38,0.34,0.36,0.33,0.40,0.37,0.35,0.38,0.36,0.39],
  FrP: [0.18,0.22,0.20,0.25,0.21,0.19,0.24,0.28,0.22,0.20,0.25,0.23,0.26],
  PF:  [0.60,0.62,0.58,0.65,0.61,0.63,0.60,0.64,0.62,0.65,0.61,0.63,0.62],
};

export const SCHEDULE = [
  { date: "2026-04-20", time: "10:00", title: "Stortingsmøte — Votering: Prop. 142 L (formuesskatt)",    type: "votering" },
  { date: "2026-04-21", time: "10:00", title: "Stortingsmøte — Debatt: Prop. 131 L (fastlegegaranti)",   type: "debatt" },
  { date: "2026-04-22", time: "09:00", title: "Finanskomiteen — møte",                                    type: "komite" },
  { date: "2026-04-22", time: "14:00", title: "Spørretime",                                               type: "sporretime" },
  { date: "2026-04-23", time: "10:00", title: "Stortingsmøte — Votering: Prop. 131 L (fastlegegaranti)", type: "votering" },
  { date: "2026-04-24", time: "10:00", title: "Stortingsmøte — Trontaledebatt (avslutning)",             type: "debatt" },
];

export const FALLBACK_PARTY: Party = {
  id: "?",
  name: "Ukjent",
  short: "?",
  color: "var(--fg-dim)",
  seats: 0,
  leader: "—",
  side: "center",
  position: { econ: 0, social: 0 },
};

export const partyById = (id: string): Party =>
  PARTIES.find((p) => p.id === id) ?? { ...FALLBACK_PARTY, id, short: id, name: id };

export const committeeById = (id: string): Committee =>
  COMMITTEES.find((c) => c.id === id) ?? { id, name: id, short: id, members: 0, chair: "—" };

export const repById = (id: string): Representative | undefined =>
  REPRESENTATIVES.find((r) => r.id === id);

export const billById = (id: string): Bill | undefined =>
  BILLS.find((b) => b.id === id);
