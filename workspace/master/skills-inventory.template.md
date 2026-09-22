# Skills inventory — every skill you can truthfully claim, and the only wording allowed

Queried by `python bin/jobkit.py skills <folder> [--pdf ...]`. Rename to `skills-inventory.md`
once filled in; the rows below are examples, replace every one of them.

**Rules**
- A row is a claim you can defend in an interview. Add or change a row only for a skill you
  have used, and cite the evidence (a repo path, a project, a report).
- `level`: `shipped` (wrote and ran it) · `reviewed` (audited / assessed someone else's) ·
  `coursework` · `banned` (never claim; the evidence cell says why).
- `page wording` is the ONLY form allowed on a résumé. `never-say` lists stretches to refuse.
- Bullets, metrics, titles and dates still come only from `content-pool.tex` / `profile.md`.
  This file governs skills-table items and keyword spelling, nothing else.
- Aliases are `;`-separated posting spellings. No `|` inside a cell.
- `row` is the skills-table row the item belongs to. `jobkit skills` maps rows to résumé tracks:
  `Security` → security, `ML` → ai, `Backend` / `Data` / `Cloud` / `Testing` / `Project` → software;
  `Languages` and `Practices` say nothing about the track. A `Project` row stays in project
  tech-tags and bullets and never enters the skills table.

## Languages
| skill | aliases | level | evidence | page wording | row | never-say |
|---|---|---|---|---|---|---|
| Python | Python 3 | shipped | <repo A>, <repo B> | Python | Languages | - |
| Java | - | coursework | university DSA coursework only | Java (last in Languages) | Languages | summary or bullets; Spring; any Java project |
| Rust | - | banned | 20 lines of framework boilerplate, not real Rust | - | - | any claim |

## Backend & Web
| skill | aliases | level | evidence | page wording | row | never-say |
|---|---|---|---|---|---|---|
| REST APIs | REST API; RESTful; RESTful APIs; REST | shipped | <repo A>, N endpoints | REST APIs | Backend | - |
| GraphQL | - | banned | no evidence; REST only | - | - | any claim |

## Data
| skill | aliases | level | evidence | page wording | row | never-say |
|---|---|---|---|---|---|---|
| PostgreSQL | Postgres; RDBMS | shipped | <repo A> schema, N tables | PostgreSQL | Data | DBA work; tuning at scale |

## Cloud & Infra
| skill | aliases | level | evidence | page wording | row | never-say |
|---|---|---|---|---|---|---|
| AWS | Amazon Web Services; cloud | shipped | <repo B> infrastructure stack | AWS (Lambda, IAM) | Cloud | S3; EC2; RDS |
| CI/CD | CI; continuous integration; continuous delivery | shipped | <repo A> GitHub Actions workflow | CI/CD (GitHub Actions) | Cloud | Jenkins; automated production deploys |

## ML & AI
| skill | aliases | level | evidence | page wording | row | never-say |
|---|---|---|---|---|---|---|
| LLM APIs | LLM; LLMs; large language models; generative AI | shipped | <repo A> provider integration | LLM APIs (<providers>) | ML | fine-tuning; training LLMs |

## Testing
| skill | aliases | level | evidence | page wording | row | never-say |
|---|---|---|---|---|---|---|
| pytest | unit testing; unit tests; automated testing | shipped | <repo A>, N tests | pytest | Testing | TDD everywhere |

## Security
| skill | aliases | level | evidence | page wording | row | never-say |
|---|---|---|---|---|---|---|
| OWASP Top 10 | OWASP; application security; AppSec | reviewed | <assessment report> | OWASP Top 10 | Security | penetration test |

## Practices
| skill | aliases | level | evidence | page wording | row | never-say |
|---|---|---|---|---|---|---|
| code review | code reviews; pull requests; peer review | shipped | <where you reviewed code> | code review | Practices | - |
| Agile | Scrum; sprints; Jira; Kanban | banned | no evidence | - | - | any claim |
