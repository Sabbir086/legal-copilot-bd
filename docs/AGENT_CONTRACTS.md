# Agent Contracts and Evidence Rules

## Shared agent output contract

Every agent must return structured data with:

- `task_status`: completed, partial, blocked or failed.
- `jurisdiction`: explicit jurisdiction or `unknown`.
- `findings`: typed results; never free-form claims alone for downstream legal decisions.
- `evidence`: exact document page/section or legal-source locator for each material finding.
- `source_refs`: stable source IDs/URLs and source-version IDs.
- `verification_status`: unverified, source_text_matched, current_status_checked, applicability_reviewed or verified.
- `limitations`: missing information and unresolved ambiguities.

## Initial agent responsibilities

### Intake and routing agent
Classifies the user's task and document type. It may route a task but cannot decide authenticity, ownership, guilt, liability or legal outcome.

### Document intelligence agent
Extracts source text and structured facts. Every extracted field must retain a page/paragraph/table locator and extraction confidence. OCR-uncertain characters must be visibly marked.

### Risk detection agent
Identifies distinct non-obvious contractual/compliance risks. It must quote a continuous verbatim passage from the uploaded document and identify its page/clause. Three is a competition acceptance target, not permission to invent findings.

### Legal research agent
Retrieves relevant law and cases from the selected jurisdiction. It must not cite a model-generated source or a search snippet as authoritative law.

### Citation verification agent
Runs independently from the research agent. It checks exact act/section text, source authority, version, amendments, repeal/status, commencement/effective date and relevance/applicability. Any failed or incomplete check remains unverified.

### Case analysis agent
Separates pleadings/allegations, admitted facts, disputed facts, evidence, submissions and judicial findings. Plaintiff/defendant analysis must remain balanced and evidence-led.

### Memorandum agent
Can only use findings that carry their source/evidence status. It must label unverified authorities and not promote them to verified.

## Evidence hierarchy

1. User-supplied document (evidence only of what that document says; not necessarily truth/authenticity).
2. Official primary legislation/gazette and official court judgment/order.
3. Official court/agency procedural pages and authenticated datasets.
4. Secondary legal commentary, used for discovery/context only unless expressly labeled.
5. Model knowledge, never sufficient as a verified citation.

## Critical separation

- Document quote verification is not statute citation verification.
- Statute existence is not proof that the text is current.
- Current text is not proof that the law applies to a given fact pattern.
- A court filing's allegation is not a court finding.
- A khatian/deed name is not by itself proof of current title.
