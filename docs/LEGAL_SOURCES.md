# Legal Source Strategy and Provenance

## Bangladesh primary law

The first-party legal corpus is Bangladesh law. Source acquisition should prioritize official Laws of Bangladesh / BDLaws content and official Gazette publications. Each source is imported as a versioned record; the original URL and retrieval timestamp are retained.

### Criminal procedure starting point

- The Code of Criminal Procedure, 1898 (Act No. V of 1898): https://bdlaws.minlaw.gov.bd/act-details-75.html?lang=en
- Code of Criminal Procedure (Amendment) Act, 2026 (Act No. XI of 2026): https://bdlaws.minlaw.gov.bd/act-details-1640.html?lang=en
- Official amendment publication / source trail must be retained alongside the consolidated Code.

**Current-source caution (checked 20 November 2026):** BDLaws lists the 2025 Code of Criminal Procedure Amendment Ordinance (No. 36 of 2025) and Second Amendment Ordinance (No. 41 of 2025) as repealed by the Code of Criminal Procedure (Amendment) Act, 2026. The 2026 Act specifies deemed commencement dates: section 12 from 10 July 2025 and other provisions from 10 August 2025. The source-ingestion pipeline must represent the 2026 Act and repeal/transition history; it must not load the two repealed ordinances as currently operative standalone law.

The Code's current consolidated page contains amended provisions. For example, the official page records section 67A as inserted by section 7 of the 2026 Amendment Act with effect from 10 August 2025. These examples are source-acquisition notes, not a complete legal interpretation or advice.

## Additional Bangladesh legal domains

Initial acquisition queue:

- Penal Code, 1860.
- Evidence Act, 1872 (with amendments).
- Code of Civil Procedure, 1908.
- Contract Act, 1872.
- Specific Relief Act, 1877.
- Relevant special criminal statutes and procedural rules.
- Supreme Court of Bangladesh judgments and official court rules/procedure material.
- Official judicial-service information, with links and retrieval timestamps.

This queue is not a claim that these materials have already been ingested or verified.

## Competition-brief example sources

The AI Builders Congress brief lists CourtListener, EUR-Lex, USPTO Open Data, Harvard Law School Caselaw Access Project and Open Legal Data. These are useful for their respective jurisdictions and data types. They are not substitutes for Bangladesh primary law. The app must store a source's jurisdiction and legal system and show the jurisdiction to the user.

## Source lifecycle

Recommended states:

1. `discovered` — URL or source identified.
2. `retrieved` — content downloaded from the source.
3. `parsed` — content extracted with stable section/paragraph structure.
4. `source_checked` — official publisher and source identity confirmed.
5. `version_checked` — amendment, repeal, commencement and effective-date history reconciled.
6. `legal_reviewed` — applicability/interpretation reviewed by a qualified human reviewer.

Only source records meeting the configured requirements for a task can support `verified` citations. Store the checker's identity/process, timestamp and exact source version. A web search result alone is not a verified source.

## Minimum metadata for each legal source

- source ID, title, act/case number, year, jurisdiction and language;
- court/issuer/publisher and source type;
- official URL and optional official Gazette reference;
- exact section/paragraph identifier and text;
- publication, assent, commencement and effective dates where available;
- amendment/repeal relationship and source version;
- retrieval timestamp, content hash and parser version;
- verification state, verification timestamp and reviewer/method;
- provenance links to all source records used to build the consolidated text.
