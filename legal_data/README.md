# Penal Code corpus import

`penal_code_sections.csv` contains 555 extracted records from the owner-supplied Penal Code, 1860 PDF: 511 numbered sections and 44 letter-suffixed records. All records contain extracted full section text and source page/version metadata. 381 records also have a best-effort `punishment_excerpt`; 174 have no separate excerpt. An empty excerpt does not mean the full section text is empty or that an offence carries no punishment.

Source snapshot date stored in the CSV: 2013-08-26. This is a historical source snapshot, not current-law verification. Check the PDF and current official legal sources before relying on any provision or punishment.

Import this CSV into `public.penal_code_sections` after applying migration `004_penal_code_auth_admin.sql`. Use the CSV headers and verify that the imported row count is 555.
