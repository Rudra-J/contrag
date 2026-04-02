"""
Creates 5 diverse legal contract DOCX files in uploads/ and ingests them
into the FAISS index so generate_dataset.py can produce a larger eval set.

Run from repo root:
    python create_eval_contracts.py
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from docx import Document

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── Contract text definitions ─────────────────────────────────────────────────

CONTRACTS = {
    "nda_agreement.docx": """\
NON-DISCLOSURE AGREEMENT

This Non-Disclosure Agreement ("Agreement") is entered into as of 15th February 2026 \
("Effective Date") by and between:

TechVentures Pvt. Ltd., a company incorporated under the laws of India, having its \
registered office at Hyderabad, Telangana ("Disclosing Party"),
AND
BuildRight Innovations Ltd., a company registered in India, having its principal office \
at Pune, Maharashtra ("Receiving Party").

1. DEFINITIONS
1.1 "Confidential Information" means any non-public, proprietary, or sensitive \
information disclosed by the Disclosing Party, whether in written, oral, electronic, \
or any other form, including but not limited to trade secrets, business plans, \
financial data, technical specifications, and customer lists.
1.2 "Permitted Purpose" means evaluation of a potential business collaboration \
between the parties.
1.3 "Representatives" means employees, directors, officers, advisors, or agents of \
the Receiving Party who have a need to know the Confidential Information.

2. OBLIGATIONS OF RECEIVING PARTY
2.1 The Receiving Party agrees to:
Hold all Confidential Information in strict confidence
Use the Confidential Information solely for the Permitted Purpose
Disclose Confidential Information only to its Representatives on a need-to-know basis
Implement reasonable security measures to protect Confidential Information
2.2 The Receiving Party shall not reverse engineer, disassemble, or decompile any \
prototypes, software, or tangible objects that embody the Confidential Information.
2.3 The Receiving Party shall promptly notify the Disclosing Party upon discovery of \
any unauthorized use or disclosure of Confidential Information.

3. EXCLUSIONS
3.1 The obligations under this Agreement do not apply to information that:
Is or becomes publicly available through no fault of the Receiving Party
Was rightfully known to the Receiving Party before disclosure
Is independently developed by the Receiving Party without reference to Confidential Information
Is required to be disclosed by applicable law or court order

4. TERM AND TERMINATION
4.1 This Agreement shall commence on the Effective Date and remain in force for \
2 years unless terminated earlier by either party with 30 days written notice.
4.2 Upon termination, the Receiving Party shall promptly return or destroy all \
Confidential Information, including all copies and derivative works.
4.3 The confidentiality obligations shall survive termination for a further period \
of 3 years with respect to trade secrets.

5. REMEDIES
5.1 The Receiving Party acknowledges that any breach of this Agreement may cause \
irreparable harm to the Disclosing Party.
5.2 The Disclosing Party shall be entitled to seek injunctive relief, specific \
performance, and any other equitable or legal remedies available without the \
requirement to post a bond.
5.3 All remedies are cumulative and non-exclusive.

6. GOVERNING LAW AND JURISDICTION
This Agreement shall be governed by and construed in accordance with the laws of India. \
The courts of Hyderabad, Telangana shall have exclusive jurisdiction over any disputes \
arising under this Agreement.

7. GENERAL PROVISIONS
7.1 This Agreement constitutes the entire agreement between the parties regarding \
confidentiality and supersedes all prior discussions on the subject.
7.2 This Agreement may not be amended except by a written instrument signed by both parties.
7.3 If any provision is found to be unenforceable, the remaining provisions shall \
continue in full force.

SIGNATURES
For TechVentures Pvt. Ltd.
Name: Arun Mehta
Designation: CEO
Date: 15/02/2026

For BuildRight Innovations Ltd.
Name: Priya Kapoor
Designation: Director
Date: 15/02/2026
""",

    "employment_agreement.docx": """\
EMPLOYMENT AGREEMENT

This Employment Agreement ("Agreement") is made and entered into as of 1st March 2026 \
("Commencement Date") between:

NextGen Software Ltd., a company incorporated under the Companies Act, 2013, having its \
registered office at Chennai, Tamil Nadu ("Employer"),
AND
Arjun Sharma, residing at Bengaluru, Karnataka ("Employee").

1. POSITION AND DUTIES
1.1 The Employer hereby employs the Employee in the position of Senior Software Engineer.
1.2 The Employee shall report directly to the Engineering Manager.
1.3 The Employee's primary duties include:
Designing and developing scalable backend systems
Conducting code reviews and mentoring junior engineers
Collaborating with cross-functional teams on product delivery
Participating in architecture discussions and technical planning
1.4 The Employer reserves the right to reasonably modify the Employee's duties \
provided such modifications are consistent with the Employee's role and experience.

2. COMPENSATION AND BENEFITS
2.1 Base Salary: INR 24,00,000 per annum (Rupees Twenty-Four Lakhs), payable \
in equal monthly instalments on the last working day of each month.
2.2 Performance Bonus: Up to 15% of annual base salary, subject to meeting \
individual and company performance targets as determined annually.
2.3 Benefits include:
Health insurance coverage for Employee and immediate family
Provident Fund contributions as per applicable law
18 days paid annual leave per year
10 days sick leave per year
5 days casual leave per year
2.4 Expenses reasonably incurred in the course of employment shall be reimbursed \
within 30 days of submission of valid receipts.

3. WORKING HOURS AND LOCATION
3.1 Standard working hours are 9:00 AM to 6:00 PM, Monday to Friday.
3.2 The Employee's primary work location shall be the Employer's office in Bengaluru.
3.3 Remote work may be permitted at the discretion of the Engineering Manager \
for up to 3 days per week.
3.4 The Employee may be required to work outside standard hours during critical \
project phases, with reasonable advance notice.

4. INTELLECTUAL PROPERTY
4.1 All inventions, discoveries, developments, software, and works of authorship \
created by the Employee in the course of employment shall be the exclusive property \
of the Employer.
4.2 The Employee agrees to promptly disclose all such creations to the Employer \
and to execute all documents necessary to assign ownership.
4.3 This clause does not apply to inventions developed entirely on the Employee's \
own time without using the Employer's resources, provided they do not relate to \
the Employer's business.

5. CONFIDENTIALITY
5.1 During and after employment, the Employee shall maintain strict confidentiality \
of all proprietary information, including source code, client lists, business strategies, \
financial data, and technical architectures.
5.2 The Employee shall not use such information for personal gain or disclose it \
to any third party.
5.3 Confidentiality obligations survive termination for a period of 5 years.

6. NON-COMPETE AND NON-SOLICITATION
6.1 For 12 months following termination, the Employee shall not:
Join or establish a direct competitor company within India
Solicit any client or customer of the Employer
Recruit or encourage any employee of the Employer to resign
6.2 This restriction is limited to activities that directly compete with the \
Employer's core product lines.

7. TERMINATION
7.1 Either party may terminate this Agreement with 90 days written notice.
7.2 The Employer may terminate immediately for cause, including:
Gross misconduct or fraud
Material breach of this Agreement not cured within 10 days of notice
Conviction for a criminal offence
7.3 Upon termination, the Employee shall return all company property, devices, \
and access credentials within 3 business days.

8. GOVERNING LAW
This Agreement shall be governed by the laws of India. The courts of Chennai, \
Tamil Nadu shall have exclusive jurisdiction.

SIGNATURES
For NextGen Software Ltd.
Name: Kavitha Rajan
Designation: HR Director
Date: 01/03/2026

Employee Acknowledgement
Name: Arjun Sharma
Date: 01/03/2026
""",

    "commercial_lease.docx": """\
COMMERCIAL LEASE AGREEMENT

This Commercial Lease Agreement ("Lease") is entered into on 1st April 2026 \
("Commencement Date") between:

Prestige Properties Pvt. Ltd., a company registered under the Companies Act, 2013, \
having its office at Mumbai, Maharashtra ("Landlord"),
AND
Orbit Retail Solutions Ltd., a company incorporated in India, having its principal \
place of business at Mumbai, Maharashtra ("Tenant").

1. PREMISES
1.1 The Landlord hereby leases to the Tenant the commercial premises located at \
Unit 4B, Prestige Business Tower, Andheri East, Mumbai — 400069, comprising \
approximately 2,800 square feet of office space ("Premises").
1.2 The Premises are to be used solely for the purpose of operating a retail \
technology company and related administrative activities.
1.3 The Tenant shall not use the Premises for any illegal, immoral, or hazardous \
activity.

2. LEASE TERM
2.1 The Lease shall commence on 1st April 2026 and expire on 31st March 2029, \
a period of 3 years ("Lease Term").
2.2 The Tenant shall have the option to renew for a further term of 2 years \
by providing written notice at least 90 days before expiry.
2.3 Renewal shall be at a rent to be mutually agreed, not exceeding 15% above \
the prevailing rent at the time of renewal.

3. RENT AND PAYMENTS
3.1 Monthly Rent: INR 1,40,000 (One Lakh Forty Thousand) per month, payable \
in advance by the 5th of each month.
3.2 Security Deposit: INR 4,20,000 (Three months' rent), payable on the \
Commencement Date and refundable within 30 days of vacating the Premises, \
subject to deductions for damage or unpaid dues.
3.3 Late payment of rent beyond 10 days shall attract a penalty of 2% per month \
on the outstanding amount.
3.4 Annual rent escalation of 8% shall apply at the beginning of each lease year.

4. MAINTENANCE AND REPAIRS
4.1 The Tenant shall maintain the Premises in good and tenantable condition, \
including routine cleaning, minor repairs, and upkeep of fixtures.
4.2 The Landlord shall be responsible for structural repairs, external walls, \
roof, and major mechanical systems (HVAC, lifts, plumbing).
4.3 The Tenant shall not make structural alterations, additions, or improvements \
without prior written consent from the Landlord.
4.4 The Tenant shall permit the Landlord to inspect the Premises with 48 hours \
advance notice.

5. UTILITIES AND SERVICES
5.1 The Tenant shall be responsible for payment of all utility charges including \
electricity, water, internet, and telephone.
5.2 Common area maintenance charges (CAM) of INR 15,000 per month are payable \
by the Tenant in addition to rent.
5.3 The Landlord shall ensure uninterrupted power backup and security services \
for the building.

6. INSURANCE
6.1 The Tenant shall obtain and maintain comprehensive general liability insurance \
covering public liability, property damage, and business interruption.
6.2 The minimum coverage shall be INR 50,00,000 per incident.
6.3 The Landlord shall maintain insurance for the building structure.

7. TERMINATION AND VACATING
7.1 The Tenant may terminate the Lease early by giving 3 months written notice \
and paying a termination fee equal to 2 months' rent.
7.2 The Landlord may terminate if the Tenant:
Fails to pay rent for 2 consecutive months
Causes substantial damage to the Premises
Violates any material term of this Lease
7.3 Upon expiry or termination, the Tenant shall vacate the Premises, remove all \
personal property, and restore the Premises to original condition, fair wear \
and tear excepted.

8. GOVERNING LAW
This Lease shall be governed by the laws of Maharashtra. The courts of Mumbai \
shall have exclusive jurisdiction.

SIGNATURES
For Prestige Properties Pvt. Ltd.
Name: Ranjit Desai
Designation: Managing Director
Date: 01/04/2026

For Orbit Retail Solutions Ltd.
Name: Meera Iyer
Designation: CEO
Date: 01/04/2026
""",

    "software_license.docx": """\
SOFTWARE LICENSE AGREEMENT

This Software License Agreement ("Agreement") is entered into as of 10th January 2026 \
("Effective Date") by and between:

CoreStack Technologies Pvt. Ltd., a company incorporated under Indian law, having its \
registered office at Bengaluru, Karnataka ("Licensor"),
AND
FinEdge Capital Pvt. Ltd., a company incorporated under Indian law, having its \
principal office at Delhi, NCR ("Licensee").

1. DEFINITIONS
1.1 "Software" means the proprietary financial analytics platform known as "StackAnalytics v3.0", \
including all modules, updates, documentation, APIs, and associated materials.
1.2 "License Key" means the unique activation credential issued to the Licensee \
for each authorized installation.
1.3 "Authorized Users" means employees and contractors of the Licensee who are \
permitted to access the Software.
1.4 "Source Code" means the human-readable form of the Software.

2. GRANT OF LICENSE
2.1 Subject to the terms of this Agreement, the Licensor grants the Licensee \
a non-exclusive, non-transferable, revocable license to:
Install and use the Software on up to 50 devices within the Licensee's network
Allow access to a maximum of 200 Authorized Users
Integrate the Software's APIs with Licensee's internal systems
Create backups of the Software for disaster recovery purposes
2.2 The Licensee may not sublicense, resell, distribute, or transfer the Software \
to any third party.
2.3 The Licensee shall not modify, adapt, translate, or create derivative works \
based on the Software without prior written consent.

3. LICENSE FEES AND PAYMENT
3.1 Annual License Fee: INR 36,00,000 (Thirty-Six Lakhs) for the first year, \
invoiced 30 days prior to the start of each annual term.
3.2 Payment is due within 30 days of invoice.
3.3 Late payments shall accrue interest at 1.5% per month.
3.4 The Licensor reserves the right to suspend access to the Software if payment \
is overdue by more than 45 days.
3.5 License fees are non-refundable once the annual term has commenced.

4. SUPPORT AND MAINTENANCE
4.1 The Licensor shall provide:
Standard technical support via email on business days, with response within 24 hours
Critical bug fixes released within 5 business days of confirmed report
Minor updates and patches at no additional cost
Access to an online knowledge base and documentation portal
4.2 Major version upgrades may be available at a discounted rate of 30% of the \
standard upgrade fee for existing licensees.
4.3 Support excludes issues arising from unauthorized modifications or integration \
with non-approved third-party systems.

5. INTELLECTUAL PROPERTY
5.1 All intellectual property rights in the Software, including source code, \
algorithms, user interface, and documentation, remain exclusively with the Licensor.
5.2 The Licensee acquires no ownership interest in the Software by virtue of \
this Agreement.
5.3 The Licensor retains the right to use anonymized usage data to improve \
the Software, provided no personally identifiable information is included.

6. DATA SECURITY AND PRIVACY
6.1 The Licensor shall implement industry-standard security measures including \
AES-256 encryption, role-based access controls, and regular penetration testing.
6.2 The Licensor shall notify the Licensee within 48 hours of discovering any \
data breach affecting the Licensee's data.
6.3 Data processed by the Software shall be stored within India unless the \
Licensee explicitly consents to cross-border transfer.

7. LIMITATION OF LIABILITY
7.1 The Licensor's total liability under this Agreement shall not exceed the \
total license fees paid in the 12 months preceding the event giving rise to liability.
7.2 Neither party shall be liable for indirect, incidental, or consequential \
damages including loss of profits or data.
7.3 The Licensee is responsible for maintaining data backups and disaster \
recovery procedures.

8. TERM AND TERMINATION
8.1 This Agreement shall commence on the Effective Date and continue for 1 year, \
automatically renewing for successive 1-year terms unless either party provides \
60 days written notice of non-renewal.
8.2 Either party may terminate immediately upon material breach if the breach \
is not cured within 20 days of written notice.
8.3 Upon termination, the Licensee shall uninstall the Software, destroy all \
copies, and certify destruction in writing within 14 days.

9. GOVERNING LAW
This Agreement shall be governed by the laws of India. The courts of Bengaluru, \
Karnataka shall have exclusive jurisdiction over disputes.

SIGNATURES
For CoreStack Technologies Pvt. Ltd.
Name: Vikram Nair
Designation: Chief Executive Officer
Date: 10/01/2026

For FinEdge Capital Pvt. Ltd.
Name: Sunita Bose
Designation: CTO
Date: 10/01/2026
""",

    "contractor_agreement.docx": """\
INDEPENDENT CONTRACTOR AGREEMENT

This Independent Contractor Agreement ("Agreement") is entered into as of 5th February 2026 \
("Effective Date") between:

Nexus Digital Agency Pvt. Ltd., a company incorporated under Indian law, having its \
registered office at Bengaluru, Karnataka ("Company"),
AND
Rahul Verma, an individual residing at Bengaluru, Karnataka ("Contractor").

1. ENGAGEMENT AND SERVICES
1.1 The Company engages the Contractor to provide the following services ("Services"):
UI/UX design for the Company's client projects
Creation of wireframes, prototypes, and high-fidelity mockups
Participation in design reviews and client presentations
Delivery of production-ready design assets (Figma, SVG, PNG)
1.2 The Contractor shall deliver all Services in accordance with the project briefs \
and timelines agreed upon in separate work orders ("Project Orders").
1.3 The Company may issue Project Orders as needed; the Contractor is not obligated \
to accept but must notify the Company within 3 business days of receipt.

2. CONTRACTOR STATUS
2.1 The Contractor is an independent contractor and not an employee, agent, or \
partner of the Company.
2.2 The Contractor is solely responsible for:
Payment of all applicable taxes, including income tax and GST
Maintaining own equipment, software, and workspace
Obtaining any professional licences required for the Services
Providing own liability insurance
2.3 The Contractor shall have no authority to bind the Company in any contract \
or obligation.

3. COMPENSATION
3.1 Fixed Rate: INR 8,000 per design day (8 hours), as specified in each Project Order.
3.2 Milestone payments shall be made within 15 days of delivery and acceptance \
of each milestone.
3.3 The Company shall reimburse pre-approved expenses, including licensed font \
purchases, stock assets, and prototype tools, within 30 days of invoice.
3.4 In the event of scope expansion beyond the agreed Project Order, a change \
order must be signed before additional work commences.
3.5 Invoices must include GST registration number where applicable.

4. INTELLECTUAL PROPERTY
4.1 All design work, assets, concepts, and deliverables created specifically for \
the Company or its clients under this Agreement ("Work Product") shall be assigned \
to the Company upon receipt of full payment.
4.2 The Contractor retains ownership of pre-existing tools, templates, design \
systems, and personal libraries ("Contractor IP"), which are licensed to the \
Company on a non-exclusive basis for use in the delivered Work Product.
4.3 The Contractor may showcase Work Product in a personal portfolio with prior \
written consent from the Company, unless restricted by client confidentiality.

5. CONFIDENTIALITY
5.1 The Contractor shall not disclose any proprietary information of the Company \
or its clients, including project briefs, business strategies, unreleased products, \
and client identities, to any third party.
5.2 The Contractor shall sign a separate client-specific NDA if required.
5.3 Confidentiality obligations survive termination for 2 years.

6. EXCLUSIVITY AND NON-COMPETE
6.1 The Contractor is not exclusive to the Company and may provide services to \
other clients, provided there is no conflict of interest.
6.2 The Contractor shall disclose any potential conflicts and shall not take on \
work for direct competitors of the Company's active clients during the engagement.
6.3 "Direct competitor" means a company offering substantially similar services \
in the same market segment as the Company's active client.

7. TERM AND TERMINATION
7.1 This Agreement shall remain in force from the Effective Date until terminated \
by either party with 14 days written notice.
7.2 The Company may terminate immediately if the Contractor:
Materially breaches this Agreement
Delivers work of consistently unacceptable quality despite written warnings
Violates confidentiality obligations
7.3 Upon termination, the Contractor shall deliver all work in progress and \
return any Company equipment or access credentials within 5 business days.

8. DISPUTE RESOLUTION
8.1 The parties shall attempt to resolve any dispute through good faith negotiation \
within 20 days of written notice of the dispute.
8.2 Unresolved disputes shall be referred to arbitration under the Arbitration and \
Conciliation Act, 1996.
8.3 The seat of arbitration shall be Bengaluru, and proceedings shall be in English.

9. GOVERNING LAW
This Agreement shall be governed by the laws of India. The courts of Bengaluru, \
Karnataka shall have exclusive jurisdiction.

SIGNATURES
For Nexus Digital Agency Pvt. Ltd.
Name: Deepa Krishnan
Designation: Director of Operations
Date: 05/02/2026

Contractor Acknowledgement
Name: Rahul Verma
Date: 05/02/2026
""",
}


# ── Write DOCX files ──────────────────────────────────────────────────────────

def write_docx(filename: str, text: str):
    path = os.path.join(UPLOAD_DIR, filename)
    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    doc.save(path)
    print(f"Created {path}")
    return path


# ── Ingest into FAISS ─────────────────────────────────────────────────────────

def main():
    paths = []
    for filename, text in CONTRACTS.items():
        p = write_docx(filename, text)
        paths.append(p)

    print("\nIngesting contracts into FAISS index...")
    from ingest import ingest
    for p in paths:
        ingest(p)

    print(f"\nDone. {len(paths)} contracts ingested.")
    print("Now run:  python eval/generate_dataset.py")


if __name__ == "__main__":
    main()
