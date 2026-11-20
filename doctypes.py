"""Tender document types and the phrases used to recognise them.

strong : phrases that normally appear as the *title / heading* of that document.
weak   : supporting words that only add a little to the score.

Order matters: when two types score the same, the one listed first wins,
so keep specific types above generic ones (e.g. "Non-Blacklisting Declaration"
above "Declaration / Undertaking").

You do not need to edit this file to add your own documents - use the
"Custom documents" box in the app sidebar, or create a file called
custom_doctypes.txt next to app.py (see README).
"""

from __future__ import annotations

DEFAULT_DOC_TYPES: list[dict] = [
    {
        "name": "Index",
        "strong": ["table of contents", "index of documents", "list of documents",
                   "document index", "documents index", "document checklist",
                   "documents checklist", "checklist of documents", "list of enclosures",
                   "list of annexures", "विषय सूची"],
        "weak": ["sr no", "particulars", "page no", "enclosed", "annexure"],
    },
    {
        "name": "Covering Letter",
        "strong": ["covering letter", "cover letter", "forwarding letter",
                   "letter of submission", "submission of tender", "submission of bid",
                   "tender submission letter", "bid submission letter", "letter of bid",
                   "form of tender", "form of bid"],
        "weak": ["kind attention", "we hereby submit", "we are pleased to submit",
                 "dear sir", "subject", "tender no"],
    },
    {
        "name": "GST Registration Certificate",
        "strong": ["form gst reg 06", "gst reg 06", "gst registration certificate",
                   "registration certificate gst", "gstin certificate",
                   "goods and services tax registration", "वस्तु एवं सेवा कर"],
        "weak": ["gstin", "gst", "goods and services tax", "legal name",
                 "constitution of business", "date of liability", "type of registration",
                 "composition", "additional places of business"],
    },
    {
        "name": "GST Returns",
        "strong": ["gstr 3b", "gstr 1", "gstr 9", "gstr 2b", "gst return", "gst returns",
                   "gst return filing", "form gstr", "gst turnover"],
        "weak": ["tax period", "arn", "date of filing", "outward supplies", "gstin"],
    },
    {
        "name": "Income Tax Returns (ITR)",
        "strong": ["income tax return", "indian income tax return acknowledgement",
                   "itr v", "itr 1", "itr 2", "itr 3", "itr 4", "itr 5", "itr 6",
                   "itr acknowledgement", "computation of total income", "return of income"],
        "weak": ["assessment year", "acknowledgement number", "e filing", "total income",
                 "taxes paid", "verification"],
    },
    {
        "name": "PAN Card",
        "strong": ["permanent account number card", "pan card", "e pan",
                   "income tax department govt of india", "permanent account number",
                   "स्थायी खाता संख्या"],
        "weak": ["income tax department", "pan", "govt of india", "signature",
                 "date of incorporation", "father s name", "आयकर विभाग"],
    },
    {
        "name": "Certificate of Incorporation",
        "strong": ["certificate of incorporation", "fresh certificate of incorporation",
                   "incorporation certificate", "certificate of commencement of business",
                   "निगमन प्रमाण पत्र"],
        "weak": ["registrar of companies", "corporate identity number", "cin",
                 "companies act", "ministry of corporate affairs", "roc",
                 "is this day incorporated", "limited company"],
    },
    {
        "name": "MOA & AOA",
        "strong": ["memorandum of association", "articles of association", "moa", "aoa"],
        "weak": ["company shall", "objects", "subscribers", "share capital"],
    },
    {
        "name": "Partnership Deed / LLP Agreement",
        "strong": ["partnership deed", "deed of partnership", "llp agreement",
                   "limited liability partnership agreement",
                   "certificate of registration of firm", "registrar of firms"],
        "weak": ["partners", "profit sharing ratio", "firm shall", "llpin"],
    },
    {
        "name": "Udyam (MSME) Registration",
        "strong": ["udyam registration certificate", "udyam registration", "udyog aadhaar",
                   "msme registration", "msme certificate", "ssi registration", "nsic",
                   "national small industries corporation", "udyam"],
        "weak": ["ministry of micro small and medium enterprises", "micro", "small",
                 "medium", "enterprise", "type of enterprise", "nic code",
                 "date of commencement"],
    },
    {
        "name": "Director KYC",
        "strong": ["aadhaar", "aadhar", "unique identification authority of india",
                   "director identification number", "din", "driving licence", "voter id",
                   "passport", "election commission of india", "kyc"],
        "weak": ["date of birth", "male", "female", "enrollment no", "vid"],
    },
    {
        "name": "Turnover Certificate",
        "strong": ["turnover certificate", "certificate of turnover", "annual turnover",
                   "average annual turnover", "turnover statement", "statement of turnover",
                   "ca certificate", "chartered accountant certificate", "financial turnover",
                   "turnover details"],
        "weak": ["udin", "chartered accountants", "firm registration no", "membership no",
                 "turnover", "financial year", "lakhs", "crore"],
    },
    {
        "name": "Net Worth Certificate",
        "strong": ["net worth certificate", "networth certificate", "certificate of net worth",
                   "net worth statement"],
        "weak": ["net worth", "networth", "paid up capital", "reserves and surplus", "udin"],
    },
    {
        "name": "Bank Solvency Certificate",
        "strong": ["solvency certificate", "bank solvency certificate",
                   "certificate of solvency", "banker s certificate"],
        "weak": ["solvent", "solvency", "banker", "branch manager", "creditworthy"],
    },
    {
        "name": "Audited Balance Sheet & P&L",
        "strong": ["balance sheet", "audited balance sheet", "profit and loss account",
                   "statement of profit and loss", "profit and loss statement",
                   "independent auditor s report", "auditor s report",
                   "audited financial statements", "financial statements",
                   "notes to financial statements", "cash flow statement", "trial balance"],
        "weak": ["total assets", "liabilities", "sundry debtors", "share capital",
                 "depreciation", "reserves and surplus", "current assets"],
    },
    {
        "name": "Tax Clearance / TDS",
        "strong": ["tax clearance certificate", "tax clearance", "tds certificate",
                   "form 16a", "form 26as", "26as", "tax deduction account number",
                   "no dues certificate", "tax compliance certificate"],
        "weak": ["tan", "tds", "deductor", "deductee"],
    },
    {
        "name": "EPF Registration",
        "strong": ["employees provident fund organisation", "employees provident fund",
                   "epf registration", "epfo", "provident fund code", "pf code allotment",
                   "code allotment letter", "epf code"],
        "weak": ["establishment id", "pf", "epf", "provident fund"],
    },
    {
        "name": "ESIC Registration",
        "strong": ["employees state insurance corporation", "esic registration",
                   "esi registration", "esic code", "esi code", "employer code number",
                   "employees state insurance"],
        "weak": ["esic", "esi", "insured persons", "sub regional office"],
    },
    {
        "name": "Professional Tax",
        "strong": ["professional tax registration", "professional tax enrolment",
                   "profession tax", "professional tax certificate", "ptrc", "ptec"],
        "weak": ["professional tax"],
    },
    {
        "name": "Trade / Labour License",
        "strong": ["labour license", "labour licence", "contract labour license",
                   "contract labour licence", "trade license", "trade licence",
                   "shops and establishments", "shop and establishment", "shop act",
                   "factory license", "factory licence"],
        "weak": ["licence", "license", "licensing officer", "valid up to", "renewal"],
    },
    {
        "name": "ISO Certificate",
        "strong": ["iso 9001", "iso 14001", "iso 45001", "iso 27001", "iso 22000",
                   "iso certificate", "ohsas 18001", "quality management system certificate"],
        "weak": ["accreditation", "iaf", "ukas", "nabcb", "management system",
                 "scope of certification"],
    },
    {
        "name": "Cancelled Cheque / Bank Details",
        "strong": ["cancelled cheque", "canceled cheque", "bank details",
                   "bank account details", "bank mandate form", "bank mandate",
                   "nach mandate"],
        "weak": ["ifsc", "micr", "account number", "account no", "branch"],
    },
    {
        "name": "EMD / Bid Security / Tender Fee",
        "strong": ["earnest money deposit", "earnest money", "bid security",
                   "bid security declaration", "bid securing declaration", "emd",
                   "tender fee", "tender document fee", "tender processing fee",
                   "cost of tender document", "demand draft", "neft receipt",
                   "rtgs receipt", "payment receipt"],
        "weak": ["utr", "transaction id", "ifsc", "amount paid", "payee", "dd no"],
    },
    {
        "name": "Bank Guarantee",
        "strong": ["bank guarantee", "performance bank guarantee", "performance guarantee",
                   "bid bond", "letter of guarantee"],
        "weak": ["guarantee", "beneficiary", "hereby irrevocably", "invoke",
                 "claim period", "expiry date"],
    },
    {
        "name": "Power of Attorney / Authorization Letter",
        "strong": ["power of attorney", "special power of attorney",
                   "general power of attorney", "letter of authorization",
                   "letter of authorisation", "authorization letter", "authorisation letter",
                   "authority letter", "letter of authority", "authorized signatory",
                   "authorised signatory", "authority to sign"],
        "weak": ["attorney", "authorised", "specimen signature", "hereby authorise",
                 "hereby appoint"],
    },
    {
        "name": "Board Resolution",
        "strong": ["board resolution", "resolution of the board", "extract of the minutes",
                   "certified true copy of the resolution",
                   "extract of minutes of the meeting"],
        "weak": ["resolved that", "board of directors", "meeting held on"],
    },
    {
        "name": "Non-Blacklisting Declaration",
        "strong": ["non blacklisting", "non blacklisting declaration",
                   "declaration of non blacklisting", "not been blacklisted",
                   "not blacklisted", "blacklisting declaration",
                   "declaration regarding blacklisting", "non debarment",
                   "debarment declaration", "no blacklisting",
                   "undertaking regarding blacklisting"],
        "weak": ["blacklisted", "debarred", "black listed", "banned"],
    },
    {
        "name": "Integrity Pact",
        "strong": ["integrity pact", "pre contract integrity pact",
                   "conflict of interest declaration", "code of integrity"],
        "weak": ["bidder", "principal", "corruption", "independent external monitor"],
    },
    {
        "name": "Affidavit",
        "strong": ["affidavit", "notarised affidavit", "notarized", "solemnly affirm",
                   "शपथ पत्र", "शपथपत्र"],
        "weak": ["notary", "deponent", "sworn", "stamp paper", "verified at"],
    },
    {
        "name": "Declaration / Undertaking",
        "strong": ["self declaration", "declaration cum undertaking", "undertaking",
                   "declaration", "self certification", "self certificate",
                   "declaration by the bidder", "declaration form", "घोषणा पत्र",
                   "वचन पत्र"],
        "weak": ["we hereby declare", "hereby undertake", "true and correct",
                 "i hereby declare"],
    },
    {
        "name": "JV / Consortium Agreement",
        "strong": ["joint venture agreement", "consortium agreement", "jv agreement",
                   "memorandum of understanding", "mou", "joint venture",
                   "teaming agreement", "consortium"],
        "weak": ["lead partner", "jv partner", "joint and several"],
    },
    {
        "name": "Make in India Declaration",
        "strong": ["make in india", "local content", "class i local supplier",
                   "class ii local supplier", "ppp mii", "local content certificate"],
        "weak": ["mii", "domestic value addition", "local supplier"],
    },
    {
        "name": "OEM Authorization (MAF)",
        "strong": ["manufacturer authorization", "manufacturer s authorization form",
                   "manufacturers authorization", "manufacturer authorisation", "maf",
                   "oem authorization", "oem authorisation", "dealer certificate",
                   "authorized dealer", "authorised dealer", "authorized distributor",
                   "authorised distributor", "authorized partner",
                   "authorized service provider", "dealership certificate",
                   "oem certificate"],
        "weak": ["oem", "manufacturer", "warranty", "after sales support",
                 "authorised to quote"],
    },
    {
        "name": "Past Experience",
        "strong": ["work order", "completion certificate", "experience certificate",
                   "work completion certificate", "satisfactory completion",
                   "purchase order", "letter of award", "letter of acceptance",
                   "performance certificate", "past experience", "similar work",
                   "details of similar works", "list of past experience",
                   "experience statement", "client list", "list of clients",
                   "list of projects", "project experience", "order copy",
                   "contract agreement", "work experience", "कार्य आदेश",
                   "अनुभव प्रमाण पत्र", "कार्य पूर्णता प्रमाण पत्र"],
        "weak": ["scope of work", "contract value", "date of completion", "work executed",
                 "completed successfully", "order value", "client", "project"],
    },
    {
        "name": "Company Profile",
        "strong": ["company profile", "organization profile", "organisation profile",
                   "firm profile", "bidder profile", "profile of the company",
                   "about us", "details of the bidder", "bidder information",
                   "bidder details", "general information of the bidder",
                   "particulars of the bidder", "corporate profile", "brief profile",
                   "profile of the firm"],
        "weak": ["established in", "our vision", "our mission", "registered office",
                 "directors", "years of experience"],
    },
    {
        "name": "Manpower / Key Personnel",
        "strong": ["manpower details", "list of technical staff", "key personnel",
                   "organization chart", "organisation chart", "organogram",
                   "technical manpower", "list of employees", "technical staff",
                   "qualified staff", "resume", "curriculum vitae"],
        "weak": ["qualification", "designation", "experience in years", "employee id",
                 "engineer", "supervisor"],
    },
    {
        "name": "Equipment / Machinery List",
        "strong": ["list of equipment", "plant and machinery", "machinery details",
                   "equipment list", "list of machinery", "tools and equipment",
                   "details of equipment", "equipment details", "list of plant",
                   "owned equipment"],
        "weak": ["make model", "quantity", "owned", "hired", "year of purchase",
                 "capacity"],
    },
    {
        "name": "Address Proof",
        "strong": ["rent agreement", "rental agreement", "lease deed", "lease agreement",
                   "electricity bill", "address proof", "proof of address",
                   "property tax receipt", "sale deed", "telephone bill", "water bill",
                   "ownership document"],
        "weak": ["landlord", "tenant", "lessor", "lessee", "consumer no", "meter"],
    },
    {
        "name": "Brochure / Datasheet",
        "strong": ["brochure", "catalogue", "catalog", "datasheet", "data sheet",
                   "technical datasheet", "product catalogue"],
        "weak": ["features", "specifications", "model no"],
    },
    {
        "name": "Tender Document / Acceptance",
        "strong": ["tender acceptance", "acceptance of terms and conditions",
                   "acceptance of tender conditions", "token of acceptance",
                   "acceptance letter", "acceptance of tender", "pre bid",
                   "pre bid meeting", "pre bid queries", "corrigendum", "addendum",
                   "tender document", "bid document", "request for proposal",
                   "notice inviting tender"],
        "weak": ["terms and conditions", "general conditions of contract",
                 "special conditions", "signed and stamped"],
    },
    {
        "name": "Price Bid / BOQ",
        "strong": ["price bid", "financial bid", "commercial bid", "bill of quantities",
                   "boq", "price schedule", "schedule of rates", "rate schedule",
                   "financial proposal", "price proposal", "schedule of prices",
                   "quoted rates", "commercial offer", "financial offer"],
        "weak": ["unit rate", "amount in words", "total amount", "gst extra", "quantity",
                 "rate in figures"],
    },
    {
        "name": "Technical Bid / Compliance",
        "strong": ["technical bid", "technical compliance", "compliance statement",
                   "technical specifications compliance", "technical proposal",
                   "technical offer", "statement of compliance",
                   "technical compliance statement", "compliance sheet",
                   "deviation statement", "methodology", "work plan",
                   "approach and methodology", "technical specification"],
        "weak": ["complied", "specification", "make and model", "datasheet", "deviation"],
    },
]


def parse_custom_doc_types(text: str) -> list[dict]:
    """Parse user supplied document types.

    One document per line:

        Title = phrase one | phrase two | phrase three

    Lines starting with # are ignored.  The phrases are what normally
    appears in the heading of that document (case does not matter).
    """
    out: list[dict] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, phrases = line.split("=", 1)
        name = name.strip()
        strong = [p.strip() for p in phrases.split("|") if p.strip()]
        if name and strong:
            out.append({"name": name, "strong": strong, "weak": []})
    return out
