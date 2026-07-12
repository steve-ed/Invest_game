# Full UK Local Authority → NUTS2 → NUTS1 → Country mapping
# Structure: "Local Authority": (NUTS2, NUTS1, Country)

ONS_REGIONS = {

    # ============================
    # NUTS1: EAST OF ENGLAND (UKH)
    # ============================
    "Colchester": ("UKH1", "UKH", "England"),
    "Chelmsford": ("UKH1", "UKH", "England"),
    "Tendring": ("UKH1", "UKH", "England"),
    "Maldon": ("UKH1", "UKH", "England"),
    "Braintree": ("UKH1", "UKH", "England"),
    "Uttlesford": ("UKH1", "UKH", "England"),
    "Harlow": ("UKH1", "UKH", "England"),
    "Epping Forest": ("UKH1", "UKH", "England"),
    "Brentwood": ("UKH1", "UKH", "England"),
    "Basildon": ("UKH1", "UKH", "England"),
    "Castle Point": ("UKH1", "UKH", "England"),
    "Rochford": ("UKH1", "UKH", "England"),
    "Southend-on-Sea": ("UKH1", "UKH", "England"),
    "Thurrock": ("UKH1", "UKH", "England"),
    "Cambridge": ("UKH1", "UKH", "England"),
    "South Cambridgeshire": ("UKH1", "UKH", "England"),
    "Huntingdonshire": ("UKH1", "UKH", "England"),
    "Fenland": ("UKH1", "UKH", "England"),
    "East Cambridgeshire": ("UKH1", "UKH", "England"),
    "Peterborough": ("UKH1", "UKH", "England"),
    "Norwich": ("UKH1", "UKH", "England"),
    "Broadland": ("UKH1", "UKH", "England"),
    "South Norfolk": ("UKH1", "UKH", "England"),
    "Great Yarmouth": ("UKH1", "UKH", "England"),
    "North Norfolk": ("UKH1", "UKH", "England"),
    "King's Lynn and West Norfolk": ("UKH1", "UKH", "England"),
    "Breckland": ("UKH1", "UKH", "England"),
    "Ipswich": ("UKH1", "UKH", "England"),
    "East Suffolk": ("UKH1", "UKH", "England"),
    "West Suffolk": ("UKH1", "UKH", "England"),

    # Hertfordshire (UKH2)
    "Hertsmere": ("UKH2", "UKH", "England"),
    "Watford": ("UKH2", "UKH", "England"),
    "St Albans": ("UKH2", "UKH", "England"),
    "Dacorum": ("UKH2", "UKH", "England"),
    "Three Rivers": ("UKH2", "UKH", "England"),
    "Welwyn Hatfield": ("UKH2", "UKH", "England"),
    "East Hertfordshire": ("UKH2", "UKH", "England"),
    "North Hertfordshire": ("UKH2", "UKH", "England"),
    "Stevenage": ("UKH2", "UKH", "England"),
    "Broxbourne": ("UKH2", "UKH", "England"),

    # Bedfordshire & Milton Keynes (UKH3)
    "Bedford": ("UKH3", "UKH", "England"),
    "Central Bedfordshire": ("UKH3", "UKH", "England"),
    "Luton": ("UKH3", "UKH", "England"),
    "Milton Keynes": ("UKH3", "UKH", "England"),

    # ============================
    # NUTS1: LONDON (UKI)
    # ============================
    # Inner London West (UKI3)
    "Camden": ("UKI3", "UKI", "England"),
    "Westminster": ("UKI3", "UKI", "England"),
    "Kensington and Chelsea": ("UKI3", "UKI", "England"),
    "Hammersmith and Fulham": ("UKI3", "UKI", "England"),
    "Wandsworth": ("UKI3", "UKI", "England"),

    # Inner London East (UKI4)
    "Hackney": ("UKI4", "UKI", "England"),
    "Tower Hamlets": ("UKI4", "UKI", "England"),
    "Islington": ("UKI4", "UKI", "England"),
    "Haringey": ("UKI4", "UKI", "England"),
    "Newham": ("UKI4", "UKI", "England"),
    "Lambeth": ("UKI4", "UKI", "England"),
    "Southwark": ("UKI4", "UKI", "England"),
    "Lewisham": ("UKI4", "UKI", "England"),

    # Outer London East & NE (UKI5)
    "Barking and Dagenham": ("UKI5", "UKI", "England"),
    "Havering": ("UKI5", "UKI", "England"),
    "Redbridge": ("UKI5", "UKI", "England"),
    "Waltham Forest": ("UKI5", "UKI", "England"),
    "Enfield": ("UKI5", "UKI", "England"),
    "Bexley": ("UKI5", "UKI", "England"),
    "Greenwich": ("UKI5", "UKI", "England"),

    # Outer London South (UKI6)
    "Croydon": ("UKI6", "UKI", "England"),
    "Sutton": ("UKI6", "UKI", "England"),
    "Bromley": ("UKI6", "UKI", "England"),
    "Merton": ("UKI6", "UKI", "England"),
    "Kingston upon Thames": ("UKI6", "UKI", "England"),
    "Richmond upon Thames": ("UKI6", "UKI", "England"),

    # Outer London West & NW (UKI7)
    "Barnet": ("UKI7", "UKI", "England"),
    "Brent": ("UKI7", "UKI", "England"),
    "Ealing": ("UKI7", "UKI", "England"),
    "Harrow": ("UKI7", "UKI", "England"),
    "Hillingdon": ("UKI7", "UKI", "England"),
    "Hounslow": ("UKI7", "UKI", "England"),

    # ============================
    # NUTS1: SOUTH EAST (UKJ)
    # ============================
    # Berkshire, Buckinghamshire & Oxfordshire (UKJ1)
    "Oxford": ("UKJ1", "UKJ", "England"),
    "Cherwell": ("UKJ1", "UKJ", "England"),
    "South Oxfordshire": ("UKJ1", "UKJ", "England"),
    "Vale of White Horse": ("UKJ1", "UKJ", "England"),
    "West Oxfordshire": ("UKJ1", "UKJ", "England"),
    "Reading": ("UKJ1", "UKJ", "England"),
    "Wokingham": ("UKJ1", "UKJ", "England"),
    "Bracknell Forest": ("UKJ1", "UKJ", "England"),
    "Windsor and Maidenhead": ("UKJ1", "UKJ", "England"),
    "Slough": ("UKJ1", "UKJ", "England"),
    "Buckinghamshire": ("UKJ1", "UKJ", "England"),

    # Surrey, East & West Sussex (UKJ2)
    "Brighton and Hove": ("UKJ2", "UKJ", "England"),
    "Adur": ("UKJ2", "UKJ", "England"),
    "Worthing": ("UKJ2", "UKJ", "England"),
    "Arun": ("UKJ2", "UKJ", "England"),
    "Chichester": ("UKJ2", "UKJ", "England"),
    "Horsham": ("UKJ2", "UKJ", "England"),
    "Crawley": ("UKJ2", "UKJ", "England"),
    "Mid Sussex": ("UKJ2", "UKJ", "England"),
    "Eastbourne": ("UKJ2", "UKJ", "England"),
    "Lewes": ("UKJ2", "UKJ", "England"),
    "Rother": ("UKJ2", "UKJ", "England"),
    "Hastings": ("UKJ2", "UKJ", "England"),
    "Guildford": ("UKJ2", "UKJ", "England"),
    "Waverley": ("UKJ2", "UKJ", "England"),
    "Surrey Heath": ("UKJ2", "UKJ", "England"),
    "Woking": ("UKJ2", "UKJ", "England"),
    "Elmbridge": ("UKJ2", "UKJ", "England"),
    "Epsom and Ewell": ("UKJ2", "UKJ", "England"),
    "Mole Valley": ("UKJ2", "UKJ", "England"),
    "Reigate and Banstead": ("UKJ2", "UKJ", "England"),
    "Tandridge": ("UKJ2", "UKJ", "England"),

    # Kent (UKJ4)
    "Ashford": ("UKJ4", "UKJ", "England"),
    "Canterbury": ("UKJ4", "UKJ", "England"),
    "Dartford": ("UKJ4", "UKJ", "England"),
    "Dover": ("UKJ4", "UKJ", "England"),
    "Folkestone and Hythe": ("UKJ4", "UKJ", "England"),
    "Gravesham": ("UKJ4", "UKJ", "England"),
    "Maidstone": ("UKJ4", "UKJ", "England"),
    "Sevenoaks": ("UKJ4", "UKJ", "England"),
    "Swale": ("UKJ4", "UKJ", "England"),
    "Thanet": ("UKJ4", "UKJ", "England"),
    "Tonbridge and Malling": ("UKJ4", "UKJ", "England"),
    "Tunbridge Wells": ("UKJ4", "UKJ", "England"),
    "Medway": ("UKJ4", "UKJ", "England"),

    # ============================
    # NUTS1: SOUTH WEST (UKK)
    # ============================
    "Bristol": ("UKK1", "UKK", "England"),
    "South Gloucestershire": ("UKK1", "UKK", "England"),
    "Bath and North East Somerset": ("UKK1", "UKK", "England"),
    "North Somerset": ("UKK1", "UKK", "England"),
    "Wiltshire": ("UKK1", "UKK", "England"),
    "Swindon": ("UKK1", "UKK", "England"),
    "Gloucester": ("UKK1", "UKK", "England"),
    "Cheltenham": ("UKK1", "UKK", "England"),
    "Tewkesbury": ("UKK1", "UKK", "England"),
    "Stroud": ("UKK1", "UKK", "England"),
    "Cotswold": ("UKK1", "UKK", "England"),
    "Forest of Dean": ("UKK1", "UKK", "England"),

    "Dorset": ("UKK2", "UKK", "England"),
    "BCP": ("UKK2", "UKK", "England"),
    "Somerset": ("UKK2", "UKK", "England"),

    "Cornwall": ("UKK3", "UKK", "England"),
    "Isles of Scilly": ("UKK3", "UKK", "England"),

    # ============================
    # NUTS1: WEST MIDLANDS (UKG)
    # ============================
    "Birmingham": ("UKG3", "UKG", "England"),
    "Coventry": ("UKG3", "UKG", "England"),
    "Dudley": ("UKG3", "UKG", "England"),
    "Sandwell": ("UKG3", "UKG", "England"),
    "Solihull": ("UKG3", "UKG", "England"),
    "Walsall": ("UKG3", "UKG", "England"),
    "Wolverhampton": ("UKG3", "UKG", "England"),

    "Shropshire": ("UKG2", "UKG", "England"),
    "Telford and Wrekin": ("UKG2", "UKG", "England"),
    "Staffordshire": ("UKG2", "UKG", "England"),
    "Stoke-on-Trent": ("UKG2", "UKG", "England"),

    "Herefordshire": ("UKG1", "UKG", "England"),
    "Worcestershire": ("UKG1", "UKG", "England"),
    "Warwickshire": ("UKG1", "UKG", "England"),

    # ============================
    # NUTS1: EAST MIDLANDS (UKF)
    # ============================
    "Derby": ("UKF1", "UKF", "England"),
    "Derbyshire": ("UKF1", "UKF", "England"),
    "Nottingham": ("UKF1", "UKF", "England"),
    "Nottinghamshire": ("UKF1", "UKF", "England"),

    "Leicester": ("UKF2", "UKF", "England"),
    "Leicestershire": ("UKF2", "UKF", "England"),
    "Rutland": ("UKF2", "UKF", "England"),
    "West Northamptonshire": ("UKF2", "UKF", "England"),
    "North Northamptonshire": ("UKF2", "UKF", "England"),

    "Lincolnshire": ("UKF3", "UKF", "England"),

    # ============================
    # NUTS1: NORTH WEST (UKD)
    # ============================
    "Manchester": ("UKD3", "UKD", "England"),
    "Salford": ("UKD3", "UKD", "England"),
    "Trafford": ("UKD3", "UKD", "England"),
    "Stockport": ("UKD3", "UKD", "England"),
    "Tameside": ("UKD3", "UKD", "England"),
    "Oldham": ("UKD3", "UKD", "England"),
    "Rochdale": ("UKD3", "UKD", "England"),
    "Bury": ("UKD3", "UKD", "England"),
    "Bolton": ("UKD3", "UKD", "England"),
    "Wigan": ("UKD3", "UKD", "England"),

    "Lancashire": ("UKD4", "UKD", "England"),
    "Blackpool": ("UKD4", "UKD", "England"),
    "Blackburn with Darwen": ("UKD4", "UKD", "England"),

    "Cheshire East": ("UKD6", "UKD", "England"),
    "Cheshire West and Chester": ("UKD6", "UKD", "England"),
    "Warrington": ("UKD6", "UKD", "England"),

    "Liverpool": ("UKD7", "UKD", "England"),
    "Wirral": ("UKD7", "UKD", "England"),
    "Sefton": ("UKD7", "UKD", "England"),
    "Knowsley": ("UKD7", "UKD", "England"),
    "St Helens": ("UKD7", "UKD", "England"),

    # ============================
    # NUTS1: YORKSHIRE & HUMBER (UKE)
    # ============================
    "Leeds": ("UKE4", "UKE", "England"),
    "Bradford": ("UKE4", "UKE", "England"),
    "Wakefield": ("UKE4", "UKE", "England"),
    "Kirklees": ("UKE4", "UKE", "England"),
    "Calderdale": ("UKE4", "UKE", "England"),

    "Sheffield": ("UKE3", "UKE", "England"),
    "Rotherham": ("UKE3", "UKE", "England"),
    "Doncaster": ("UKE3", "UKE", "England"),
    "Barnsley": ("UKE3", "UKE", "England"),

    "North Yorkshire": ("UKE2", "UKE", "England"),
    "York": ("UKE2", "UKE", "England"),

    "Hull": ("UKE1", "UKE", "England"),
    "East Riding of Yorkshire": ("UKE1", "UKE", "England"),
    "North Lincolnshire": ("UKE1", "UKE", "England"),
    "North East Lincolnshire": ("UKE1", "UKE", "England"),

    # ============================
    # NUTS1: NORTH EAST (UKC)
    # ============================
    "Newcastle": ("UKC1", "UKC", "England"),
    "Gateshead": ("UKC1", "UKC", "England"),
    "Sunderland": ("UKC1", "UKC", "England"),
    "South Tyneside": ("UKC1", "UKC", "England"),
    "North Tyneside": ("UKC1", "UKC", "England"),
    "North