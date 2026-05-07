# can I build something like this for india

[https://github.com/nickvido/us-code](https://github.com/nickvido/us-code)

---

Yes, you absolutely can build an India equivalent of `nickvido/us-code` — in fact, the data sources and prior art already exist to make it tractable. Here's a complete breakdown:

## What `us-code` Actually Does

The project parses official XML published by the **Office of the Law Revision Counsel (OLRC)** into structured Markdown files and commits them to Git — one file per chapter. This gives you `git diff`, `git blame`, and `git checkout` across the entire history of US law, with ~60,000 sections across 53 titles committed as 13 historical snapshots back to 2013. The key insight is treating law like code: bugs = loopholes, amendments = commits, cross-references = dependencies.[^1][^2]

## India's Equivalent Data Source

The direct counterpart to the OLRC is **India Code** (`indiacode.nic.in`), a digital repository maintained by the Legislative Department under the Ministry of Law and Justice. It hosts all enforced Central and State Acts, linked with subordinate legislation (Rules, Regulations, Notifications, Orders, etc.). The site runs on DSpace and acts are available as **PDFs and bitstream downloads**, browsable by year, title, act number, and ministry.[^3][^4][^5]

The key challenge vs. the US: India Code does **not** publish clean bulk XML the way OLRC does. The US source is a well-structured USLM XML that the ingestion tools parse directly, whereas India Code primarily serves PDFs.[^6]

## Existing Machine-Readable Sources You Can Use

You're not starting from zero — several open datasets already exist:

- **Nyaaya / nyaayaIN/laws-of-india** — Vidhi Centre for Legal Policy's repo of Indian laws in **Akoma Ntoso (AKN) XML format**, an international standard for legislative documents, licensed CC BY-NC-SA 4.0. The `consolidated/` folder has XMLs reflecting recent amendments. This is the closest analog to OLRC XML.[^7][^8]
- **Zenodo dataset** — 858 Central Acts from 1838–2020 converted from India Code PDFs to **structured JSON** using `pdfminer`, with metadata (title, enactment date, act number) extracted via regex. Already done work you can build on.[^3]
- **india.gov.in Open Data Platform** — `data.gov.in` publishes government datasets in CSV, XLS, JSON, XML, and RDF.[^9]

## How to Build It: Step-by-Step

### 1. Ingestion — scrape/parse India Code PDFs

India Code stores acts at predictable bitstream URLs like `indiacode.nic.in/bitstream/123456789/{id}/1/{act}.pdf`. You'd write a scraper (Python + `requests` + `pdfminer`/`pdfplumber`) to:[^10][^11]

- Crawl the DSpace browse pages (by year or short title)[^12]
- Download each act's PDF
- Extract text and parse sections/subsections with regex or an LLM

The Zenodo dataset already did this for 858 acts and can serve as your starting point.[^3]

### 2. Structure — convert to Markdown

Mirror `us-code-tools`'s transformation pipeline, but from PDF/AKN XML → Markdown instead of USLM XML → Markdown. If you start from the Nyaaya AKN XMLs, you can write an XSLT or Python parser directly since AKN is well-structured.[^8][^6]

Recommended file granularity (same conclusion as `us-code`): **one file per chapter/part** within each Act — gives you diffable context without 60,000 tiny files.[^2]

### 3. Git history — reconstruct amendments

This is harder for India than the US. India Code doesn't publish timestamped annual XML snapshots. Strategies:

- Use **amendment acts** (e.g., "The IPC (Amendment) Act, 2013") as commits against the base act file
- Scrape the "amendment history" sections within India Code's act pages
- Use the **Bharatiya Nyaya Sanhita 2023** etc. as a separate branch/tag replacing IPC

### 4. Cross-reference graph

Parse each section for citations like *"Section 302 of the Indian Penal Code"* or *"as defined under Section 2(h) of the Act"* to build an inbound/outbound reference index — same as the `us-code` roadmap.[^1]

## Scope of Indian Law

India's legal corpus is actually **more complex** than the US Code because it has:

- **Central Acts** (~1,500+) — parliamentary legislation
- **State Acts** (28 states × hundreds of acts each)
- **Subordinate legislation** — Rules, Regulations, Notifications under each act[^4]
- **Three languages** of original drafting (English, Hindi, and regional languages)

A realistic v1 would focus on **Central Acts only in English**, analogous to the federal US Code.

## Tools \& Prior Art to Reference

| Resource | What it gives you |
| :-- | :-- |
| `nyaayaIN/laws-of-india` [^7] | AKN XML for central laws — best structured source |
| Zenodo 858-act JSON dataset [^3] | Pre-extracted JSON from PDFs, 1838–2020 |
| `indiacode.nic.in` [^4] | Authoritative source, PDF bitstreams |
| `nickvido/us-code-tools` [^6] | Ingestion engine to adapt (MIT-ish) |
| Indian Kanoon API [^13] | Search + retrieve legal docs (has `doctypes=laws` filter) |
| OpenNyAI [^14] | NLP pipeline for Indian legal text (NER, structuring) |

## The Biggest Gap

The US project's elegance comes from OLRC's **clean, versioned XML** — same schema across 13 years, parseable in a weekend. India Code has no equivalent bulk XML export. You'll spend more time in the extraction/cleaning phase. The Nyaaya AKN XMLs  partially solve this but cover only a subset of laws and haven't been updated since 2018.[^2][^8]

The most viable path: **start with the Nyaaya AKN XMLs** as your XML source (write an AKN → Markdown converter), supplement with the Zenodo JSON dataset for breadth, and write a scraper for India Code PDFs for anything missing. Use the `us-code-tools` architecture as your template. Given you're comfortable with Node.js and Python, this is a weekend-to-a-week project for a solid v1 of Central Acts.

<span style="display:none">[^15][^16][^17][^18][^19][^20][^21][^22][^23][^24][^25][^26][^27][^28][^29][^30][^31][^32][^33][^34][^35][^36][^37][^38][^39][^40][^41][^42][^43][^44][^45][^46][^47][^48][^49][^50][^51][^52][^53][^54][^55]</span>

---

[^1]: <https://github.com/nickvido/us-code/blob/main/ROADMAP.md>

[^2]: <https://v1d0b0t.github.io/blog/posts/2026-03-29-every-law-a-commit.html>

[^3]: <https://zenodo.org/records/5088102>

[^4]: <https://www.indiacode.nic.in>

[^5]: <https://www.indiacode.nic.in/handle/123456789/1362/browse?type=actyear>

[^6]: <https://github.com/nickvido/us-code-tools>

[^7]: <https://github.com/nyaayaIN/laws-of-india>

[^8]: <https://github.com/rkunal/indian-laws-akns>

[^9]: <https://services.india.gov.in/service/detail/open-government-data-platform-india-1>

[^10]: <https://www.indiacode.nic.in/bitstream/123456789/15289/1/ipc_act.pdf>

[^11]: <https://www.indiacode.nic.in/bitstream/123456789/20062/1/a202345.pdf>

[^12]: <https://www.indiacode.nic.in/handle/123456789/1362/browse?type=shorttitle>

[^13]: <https://api.indiankanoon.org/documentation/>

[^14]: <https://github.com/OpenNyAI/Opennyai>

[^15]: <https://techpolicy.press/as-india-is-set-to-implement-its-data-protection-law-what-to-make-of-it>

[^16]: <https://www.linkedin.com/posts/jcortell_github-nickvidous-code-united-states-activity-7446013259343872000-Qoue>

[^17]: <https://www.reuters.com/sustainability/boards-policy-regulation/india-strengthens-privacy-law-with-new-data-collection-rules-2025-11-14/>

[^18]: <https://egovstandards.gov.in/sites/default/files/2021-07/Implementation> Guidelines for Open API Policy for e-Governance  (National Data Highway) V1.0_0.pdf

[^19]: <https://github.com/nickvido/us-code/issues>

[^20]: <https://apisetu.gov.in/api-policy>

[^21]: <https://github.com/nickvido/us-code/pulls>

[^22]: <https://www.linkedin.com/posts/ramrastogi0708_dpdp-gdpr-activity-7338801856116154369-7fPB>

[^23]: <https://news.ycombinator.com/item?id=47621591>

[^24]: <https://www.sciencedirect.com/science/article/pii/S2352340925003774>

[^25]: <https://github.com/nickvido/us-code>

[^26]: <https://idsa.in/publisher/issuebrief/data-protection-frameworks-of-india-and-the-us-data-sovereignty-vs-market-flexibility>

[^27]: <https://groups.google.com/g/datameet/c/3BBUsxrLhjc>

[^28]: <https://services.india.gov.in/service/detail/india-code-digital-repository-of-all-central-and-state-acts>

[^29]: <https://api.indiankanoon.org>

[^30]: <https://www.atlanticcouncil.org/blogs/southasiasource/indias-new-data-bill-is-a-mixed-bag-for-privacy/>

[^31]: <https://janhavibhoir98.wixsite.com/librarybctlawcollege/open-access-bare-acts>

[^32]: <https://github.com/topics/indian-kanoon>

[^33]: <https://www.reddit.com/r/LegalAdviceIndia/comments/13pv6nr/enterprise_grade_public_api_for_court_data/>

[^34]: <https://iclg.com/practice-areas/data-protection-laws-and-regulations/india>

[^35]: <https://www.indiacode.nic.in/handle/123456789/1362>

[^36]: <https://www.reddit.com/r/legaltech/comments/1g27s09/accessing_legal_data_for_indian_courts/>

[^37]: <https://2015.index.okfn.org/dataset/legislation/>

[^38]: <https://thesai.org/Downloads/Volume16No10/Paper_50-Bridging_Machine_Readable_Code_of_Regulations.pdf>

[^39]: <https://docs.cleartax.in/cleartax-docs/e-invoicing-ksa-api/e-invoicing-ksa-api-reference/generating-e-invoice/generate-e-invoice-via-xml>

[^40]: <https://blogs.worldbank.org/en/opendata/machine-readable-open-data-how-it-s-applicable-developing-countries>

[^41]: <https://ihsn.github.io/nada-documentation/admin-guide/web-ui/studies.html>

[^42]: <https://datasociety.net/wp-content/uploads/2024/04/Keywords_OpenData_Raghavan_04242024.pdf>

[^43]: <https://legaldatahunter.com>

[^44]: <https://github.com/rkunal/indian-laws-akns/releases>

[^45]: <https://www.linkedin.com/posts/arupdasgupta_state-wise-digital-data-register-a-joke-on-activity-7400910941531389952-DMxL>

[^46]: <https://avantiscdnprodstorage.blob.core.windows.net/legalupdatedocs/23219/IRDAI_Information_and_Cyber_Security_Guidelines_2023_April242023.pdf>

[^47]: <https://www.facebook.com/GlobalInvestigativeJournalismNetwork/posts/-journalists-at-the-hindu-parsed-nearly-22-million-voter-records-across-three-in/1338641668304931/>

[^48]: <https://www.indiacode.nic.in/repealed-act/repealed-act.jsp?locale=en>

[^49]: <https://inbiz.in.gov/Assets/IndianaUCCXML_ImplementationGuide.pdf>

[^50]: <https://www.indiacode.nic.in/?locale=hi>

[^51]: <https://developers.google.com/custom-search/docs/xml_results>

[^52]: <https://www.indiacode.nic.in/handle/123456789/1362/simple-search?page-token=9dc80e7e55c6\&page-token-value=d46843dc10f959987612fc5cb3112908\&nccharset=293057B2\&query=\&btngo=\&searchradio=all>

[^53]: <https://upload.indiacode.nic.in/showdatareport>

[^54]: <https://www.indiacode.nic.in/bitstream/123456789/15689/5/a2017-12.pdf>

[^55]: <https://www.indiacode.nic.in/handle/123456789/15351?view_type=browse>
