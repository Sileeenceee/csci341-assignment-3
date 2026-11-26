# CSCI 341 Assignment 3 – Executive Summary

**Team members**

| Name | Student ID | Contribution |
|---|---|---|
| Nurlan Mukhtar | 202376859 | Relational schema, constraints and seed data (Part 1) |
| Mukhammed Bayandin | 202298730 | SQLAlchemy queries for tasks 1–8 and the view (Part 2) |
| Abay Maratov | 202362686 | Flask web application, deployment and video (Part 3) |

**Completed work**
* Part 1: The PostgreSQL schema has 15 relations with PK, FK, NOT NULL, UNIQUE and CHECK constraints. Papers cascade to their versions. Composite FKs enforce the coordinator and chair pool rules. The seed data covers every required case: 13 users, 13 papers, 17 versions, 18 reviews and 3 conferences.
* Part 2: `part2_queries.py` runs tasks 1–8 through SQLAlchemy with bound parameters. Updates and deletes show the rows before and after the change and then roll back. The view `accepted_paper_schedule` is created and queried.
* Part 3: A Flask web app provides CRUD for users (with author and reviewer profiles), papers (with authorship, keywords and versions), reviews and sessions. It enforces the self-review and session-assignment checks in transactions and shows clear error messages. It is deployed at https://csci341-assignment3-eosin.vercel.app (Vercel) with a persistent Neon PostgreSQL database.

**Incomplete / non-working requirements:** none known.
