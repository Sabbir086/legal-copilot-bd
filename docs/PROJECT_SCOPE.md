# Legal Copilot — Product Scope (M0)

## Product identity

**Legal Copilot** is the AI Builders Congress project. It is separate from the user's other project, **LDIS**, which is being developed for the LandTech Innovation Hackathon and focuses on digital land records and land-record workflows.

Legal Copilot must not inherit LDIS-specific user roles, office workflows, registration flows, land-office administration, or its competition scope. Legal Copilot is an independent AI legal advisory and legal-document intelligence platform.

## Primary product vision

A Bengali-first and English-capable conversational legal-support platform for Bangladesh. The primary interaction is a chat interface. Users can describe a legal incident, ask procedural/legal questions, attach documents, ask questions about those documents, and request structured case or contract analysis.

## Primary jurisdiction

Bangladesh is the default jurisdiction. Other jurisdictions and international standards may be supported as explicitly selected comparative/reference jurisdictions. They must never silently be treated as Bangladesh law.

## Product capabilities

1. **General legal guidance:** incident intake, clarifying questions, issue spotting, possible legal routes, procedural information and next-step checklists.
2. **Document intelligence:** PDF/DOCX/image ingestion, extraction, document classification, summaries, clause/fact extraction and source-page references.
3. **Contract and compliance review:** identify at least three distinct, non-obvious risk signals where supported by document evidence; explain impact and recommend review/mitigation. Never invent risks to satisfy a quota.
4. **Case-file analysis:** extract parties, court, case number, dates, provisions/sections, allegations, procedural posture and cited evidence.
5. **Party-oriented analysis:** allow a user to select plaintiff/complainant/applicant or defendant/accused/respondent role; map arguments and evidence for both sides, while identifying missing facts and counterarguments. Do not coach deception, evidence fabrication or witness tampering.
6. **Bangladesh legal research:** retrieve primary statutory text, amendments, commencement/effective dates and relevant official case-law sources.
7. **Independent citation verification:** verify each legal citation against primary/authoritative source text and current status before labeling it verified.
8. **Memorandum generation:** create an evidence-linked memorandum showing sources, page/clause references, verification status, limitations and review date.
9. **Judicial-services guidance:** provide verified links and procedural directions to official services. Do not claim to file, register, pay, or perform a government action without an approved integration and explicit user authorization.

## AI Builders Congress acceptance target

The specific ask supplied for this project requires a functional multi-agent legal system that:

- ingests a raw legal document;
- identifies at least three non-obvious compliance risks, each supported by evidence in the source document; and
- generates a memorandum citing real-world statutes whose citations have been independently checked.

This requirement is a release gate for the competition prototype. A document quote match alone does not meet the citation-verification requirement. If the source evidence does not support three risks, the system must report fewer supported risks and flag the test document as unsuitable for demonstrating the three-risk acceptance scenario; it must not fabricate findings.

## Explicit non-goals for the initial release

- Replacing a licensed Bangladesh lawyer or making a court/authority decision on behalf of the user.
- Guaranteeing case outcomes, acquittal, bail, limitation calculations or legal success.
- Filing a GD, FIR, case, appeal, bail bond or court application automatically.
- Treating a model's memory or an unverified search result as legal authority.
- Silent mixing of Bangladesh law with US, EU, UK, ICC or other jurisdictional rules.

## Product language and interface

- Bengali-first UI with English support.
- Light theme.
- Chat-first layout; document analysis, citations, case analysis and memoranda are views/tools inside the same conversation workspace, not separate products.
- Show source links, jurisdiction, court/statute metadata and verification states close to the relevant answer.

## Legal-domain coverage plan

Bangladesh legal knowledge is organized into separate domains, including:

- Criminal procedure: Code of Criminal Procedure, 1898 (CrPC), with amendment and commencement tracking.
- Substantive criminal law: Penal Code, 1860 and relevant special statutes.
- Evidence: Evidence Act, 1872 and applicable amendments.
- Civil procedure, contract, property, family, labour, company, tax and other domains as authoritative corpora are acquired and reviewed.
- Judicial decisions and official procedural/service information as separate source classes.

Domain coverage must be explicitly labeled. A partial corpus must never be presented as comprehensive Bangladesh law coverage.
