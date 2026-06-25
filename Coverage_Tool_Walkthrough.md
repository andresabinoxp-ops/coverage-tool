# Coverage Tool — End-to-End Walkthrough

A single-document guide covering every step of the FMCG Coverage Tool from data upload through final rep routes. Use this to follow along during demos and to answer "what does this step actually do?" questions on the spot.

---

## 1. What the tool does (one-paragraph version)

You upload your current coverage portfolio (the stores your distributor already serves). The tool scrapes Google Places for the surrounding market universe (everything you don't yet cover), scores both groups, matches duplicates between portfolio and scrape, decides which stores deserve which visit frequency, and plans rep routes that cover the priority stores within a realistic monthly capacity. Output: per-rep daily routes, gap stores (untapped opportunities), and a per-area coverage summary.

---

## 2. Pages and the order you use them

| # | Page | What you do here |
|---|---|---|
| 1 | **Admin Settings** | One-time setup: scoring weights, size tier splits, visit benchmark defaults, API keys, optional data-aware scoring toggle |
| 2 | **Configure** | Per-market setup: country, regions/cities, portfolio upload, categories, scrape mode, region filter, direct accounts, dedicated rep rules, visit playbook, rep count |
| 3 | **Run Pipeline** | Trigger the actual run. Choose between full pipeline, geocode-only, or enrich-all modes |
| 4 | **Results** | Universe overview, coverage rates, downloads (scored universe, gap report, enriched portfolio CSV) |
| 5 | **Routes** | Rep-by-rep route map, per-day store list, uncovered outlets CSV |
| 6 | **Dashboard** | Existing-route upload + KPIs (separate from pipeline runs) |
| 7 | **Changelog** | Version history of tool improvements |

---

## 3. Configure page — every input

### 3.1 Save / Load Configuration (top of page)
- **Save Configuration** → downloads a JSON file with every Configure setting (country, regions, categories, visit playbook, rep rules, scrape mode, etc.)
- **Load Configuration** → re-uploads the JSON to restore every setting in one click after a Streamlit restart

### 3.2 Country selection
Pick a country from the dropdown. This sets the geographic search scope and defines the country's bounding box used by all downstream geocoding and scraping.

### 3.3 Portfolio upload (Current Coverage CSV)
**Required columns:** `store_name`, `address`, `city`
**Optional columns:** `store_id`, `category`, `annual_sales_usd`, `lines_per_store`, `lat`, `lng`, `district`, `region`, `postal_code`, `account`, `channel`, `fsm`, `sr`, `rating`, `review_count`, `place_id`, `phone`, `enrichment_attempted`

**Encoding support:** UTF-8 (preferred), UTF-8 BOM, CP-874/TIS-620 (Thai), GBK/Big5 (Chinese), Shift-JIS (Japanese), CP-949 (Korean), CP-1252 (Latin/Brazilian), CP-1256 (Arabic). Auto-detected in order, so you don't need to declare it.

**Mojibake repair:** if the CSV was round-tripped through Excel and accented characters look like `Atacadão`, the tool reverses the damage automatically.

**Bogus coordinate detection:** if many portfolio rows share the same lat/lng (e.g. a city centroid filled by a template), those coords are nulled and re-geocoded.

### 3.4 Region / City selection
Choose either:
- **Add Region** — select one or more states/provinces (e.g. State of Pernambuco)
- **Add City / Area** — pick specific cities (e.g. Recife, Olinda, Jaboatão)

The merged bounding box of your selections becomes the market scope.

### 3.5 Region filter (optional)
Free-text field. Type a state code or region name (`PE` for Pernambuco, `CA` for California, `Muscat` for Oman). Scraped stores whose Google address doesn't contain this text are dropped from the universe. **Skipped automatically when Scrape Mode = Cities** (because cities already restrict the scrape to the right area).

### 3.6 Scrape mode
Two options:

| Mode | How it works | When to use |
|---|---|---|
| **Rectangle (default)** | Grids the market bounding box into tiles, queries Google at each tile centre | Quick setup; for small/medium markets |
| **Cities** | Loads the list of cities inside the bbox from OpenStreetMap; you pick which ones; the scraper anchors on each selected city | Large state-wide scrapes; eliminates neighbour-state pollution |

In Cities mode:
- A "Load cities in this region" button fetches the city list using the admin-polygon query (so only true cities inside the region are returned)
- For Brazil/Malaysia/most countries this returns proper municipalities, not random villages
- For cities with 100k+ population, the tool automatically uses 2 km tiles instead of 3 km to avoid Google's 60-results-per-query cap dropping stores in dense urban areas

### 3.7 Direct accounts to exclude (optional)
Multi-line textarea. Banners serviced directly by the manufacturer (Walmart, Carrefour, Atacadão, etc.). Scraped stores whose name matches these banners are removed from the universe before scoring. Portfolio is never filtered.

### 3.8 Dedicated rep rules (optional)
Per-rule definitions for stores that must be served by a specific named rep (account-based, channel-based, or store-list rules). Remaining stores go to mixed geographic reps.

### 3.9 My Team tab
| Setting | What it does |
|---|---|
| **Rep mode** | Recommended (tool calculates rep count) vs Fixed (you set it) |
| **Rep count** | Used in Fixed mode |
| **Daily working minutes** | Default 480 (8h) |
| **Break minutes** | Default 30 — deducted from effective capacity |
| **Working days/month** | Default 22 |
| **Travel speed (km/h)** | Default 30 — effective speed including parking & traffic. 25-28 for urban Asia, 30-35 for US/Europe |
| **Store Selection %** | Recommended mode only — top N% of stores by score are routed |
| **Always route top portfolio sellers** | New: when ON, top X% of portfolio by `annual_sales_usd` are auto-included regardless of score (safety net) |

### 3.10 Visit Playbook tab
Per-category, per-tier visit frequency and duration:

| Category | Large visits/mo | Large min | Medium visits/mo | Medium min | Small visits/mo | Small min |
|---|---|---|---|---|---|---|
| Supermarket | 4 | 40 | 2 | 25 | 1 | 15 |
| Convenience | 2 | 25 | 1 | 20 | 0.5 | 15 |
| ... | ... | ... | ... | ... | ... | ... |

- Bulk CSV import/export available
- Decimals allowed (0.5 = every 2 months, 0.33 = quarterly, 0 = disable tier)

---

## 4. Run Pipeline page

### 4.1 Top: cached universe panel
Shows whether the scrape has already been cached for this market. If yes: option to download, replace by import, or repair encoding mojibake in-place.

### 4.2 Build & enrich universe (Stage 2 standalone)
Click this to scrape the market without running the full pipeline. Used to pre-build a universe cache so subsequent pipeline runs reuse it (no re-scraping cost).

### 4.3 Run options checkboxes
| Checkbox | What it does | Default |
|---|---|---|
| **Dry run mode** | No API calls, generates sample data for testing | OFF |
| **Enrich ALL portfolio stores in one pass** | Removes the 200-row cap on Stage 4 portfolio Text Search | OFF |
| **Geocode-only mode** | Runs Stage 1 only, then stops with a download button — no scrape, no scoring, no routing | OFF |

### 4.4 Cost estimate banner
Shows breakdown of expected spend:
- Geocoding cost = rows missing lat/lng × $0.005
- Portfolio enrichment cost = (rows missing rating, capped at 200 or unlimited if Enrich-ALL ticked) × $0.032
- Total estimate

### 4.5 Actual cost report
After the run, an honest cost report shows real API spend by stage. Universe cached = $0 for scraping; rows already with coords = $0 for geocoding.

---

## 5. Pipeline stages (the heart of the tool)

### Stage 1 — Portfolio geocoding
For each portfolio row that's missing lat/lng:
- Builds query: `address + district + city + region + postal_code + country`
- Calls Google Geocoding API
- Records `geocode_confidence` = `precise` / `approximate` / `failed` / `input`
- Quality check: if returned coords fall outside the market bbox + 55 km buffer → flagged `geocode_suspect = True`
- Suspect rows are re-geocoded with alternative query formats
- Survivors marked `geocode_fixed = True`

### Stage 2 — Universe scrape
Two paths depending on whether universe is already cached:

**Path A — Cache exists**
- Loads cached scrape from `st.session_state["universe_cache"]`
- Applies bbox filter to drop foreign-country stores
- Re-applies region filter + direct-accounts filter on the cached data

**Path B — Fresh scrape**
- Grids the market (bbox tiles OR city-anchored tiles)
- For each tile and each store category, calls Google Places Nearby Search
- Paginates up to 3 pages (Google's max 60 results per query)
- Filters scraped stores by relevance keywords (drops obvious cafés, banks, salons)
- Applies region filter and direct-accounts filter
- Saves the filtered universe to cache

**Encoding repair button:** appears if the cached universe has Latin-mojibake text. One click reverses it without re-scraping.

### Stage 3 — Scoring
Two-group normalisation:

**Group 1 — Portfolio (Current Coverage)**
Score = `w_rating × rating + w_reviews × log(reviews+1) + w_affluence × price_level + w_poi × poi_count + w_sales × annual_sales + w_lines × lines_per_store`

Default weights: rating 20%, reviews 25%, affluence 15%, POI 15%, sales 15%, lines 10%.

**Group 2 — Gap (Scraped)**
Score = `w_rating + w_reviews + w_affluence + w_poi` only (no sales/lines because Google doesn't have those signals).

Default weights for gap: rating 25%, reviews 25%, affluence 25%, POI 25%.

Each group is normalised 0-1 within itself, so the best portfolio store and the best gap store both reach `_norm_score = 1.0`.

**Optional: Data-aware scoring (Admin Settings checkbox, default OFF)**
When ON, portfolio stores with missing signals (rating == 0 OR reviews == 0) have those weights redistributed proportionally to the signals that ARE present. Prevents high-sales portfolio stores from getting penalised for being invisible to Google.

### Stage 4 — Coverage matching (Portfolio ↔ Scraped duplicate detection)
For each scraped store, the pipeline checks five layers in order:

| Layer | Rule | Confidence |
|---|---|---|
| **1. place_id** | Same Google place_id as a portfolio store | High |
| **2. Exact coords** | Rounded lat/lng (≈11 m) matches a portfolio store | High |
| **3. Size-aware radius** | Within base radius of a portfolio store (50 m Default, 100 m Medium, 200 m Large/known chains) | Medium |
| **4. Fuzzy name** | Within fuzzy radius (100/150/250 m) + bigram similarity ≥ 0.75 | Medium |
| **5. Chain name (new)** | Distance ≤ 500 m + bigram similarity ≥ 0.85 — catches branches where portfolio has the office address but Google has the storefront pin | Medium |

If any layer matches, the scraped store is marked `coverage_status = covered` (the portfolio already has it). Otherwise `coverage_status = gap`.

**Known chain list:** Western (Carrefour, Tesco, Lotus), Gulf (Lulu, Spinneys, Waitrose), Brazilian (Atacadão, Assaí, Pão de Açúcar, Walmart, Bompreço, BIG), Malaysian (AEON, NSK, Mydin, Econsave, KK Mart, 99 Speedmart, TF Value, KIP Mart) — all use the wider Large radius automatically.

### Stage 5 — Size tier assignment
Two paths:

**Path 1 — Portfolio stores with sales > 0**
Tier = **sales percentile** within their category:
- Top 20% by sales → Large
- Next 40% → Medium
- Bottom 40% → Small

**Path 2 — Everything else (scraped + portfolio without sales)**
Tier = **score percentile** within their category:
- Top 20% by score → Large
- Next 40% → Medium
- Bottom 40% → Small

(Sales percentile correctly tags real top-sellers as Large even when Google has no data on them. Path 2 only applies when sales data isn't available.)

Each tier maps to a visit frequency + duration from the Visit Playbook (category-specific).

### Stage 6 — Rep planning & geographic clustering
**Two modes:**

**Recommended mode**
- Combines normalised portfolio + gap scores
- Takes top N% (Store Selection %, default 60%)
- Optional: top X% of portfolio by sales are auto-added on top of the cut (Sales bypass checkbox)
- Calculates total visit time needed
- Divides by rep capacity (effective daily × working days)
- Recommends a rep count that delivers ~60–70% utilisation (sustainable target)

**Fixed mode**
- Uses the rep count you set
- Fills capacity from top-by-score downward
- Cuts off when capacity exhausted

**Geographic clustering**
- Stores partitioned by k-means clustering on lat/lng
- Capacitated balancing: 3 refinement rounds move stores between clusters until rep workload is even
- Overload split (Recommended): clusters above 110% utilisation are split iteratively until none exceed the threshold
- Daily breakdown: stores within each rep's territory are assigned to one of the 22 working days using nearest-neighbour route sorting

### Stage 7 — Place Details enrichment (optional)
For each universe store with a place_id:
- Calls Google Place Details API ($0.017 per call)
- Fetches phone, website, opening hours, formatted address, price level, rating, review count
- Skipped entirely if universe cache was used (already enriched at scrape time)

### Stage 8 — Output assembly
- Builds the scored universe DataFrame with all columns: store info + lat/lng + Google enrichment + tier + visits + rep_id + dates
- Splits into covered / gap subsets
- Computes plan_visits per store across the 2-month rolling plan
- Calculates rep utilisation, time needed, capacity

---

## 6. Results page

### 6.1 KPIs
| Metric | What it tells you |
|---|---|
| **Total universe** | Portfolio + Scraped (after duplicate matching) |
| **Currently covered** | Portfolio stores |
| **Proposed coverage** | Routed stores (portfolio + selected gap) |
| **Stores removed from original coverage** | Portfolio stores that dropped below the priority cut |
| **New stores added from gap list** | Scraped stores promoted to routes |
| **Planned visits/month** | Sum of visits across all routed stores |
| **Recommended reps** | Rep count to deliver the plan at sustainable utilisation |

### 6.2 Downloads
| File | What it contains |
|---|---|
| **Full scored universe CSV** | Every store with all columns (UTF-8 BOM so Excel reads correctly) |
| **Gap report CSV** | Scraped stores not in portfolio, with a "top gap opportunity" flag |
| **Enriched portfolio CSV** | Your original portfolio + Google enrichment fields appended; re-uploading this skips Stage 4 enrichment on future runs |
| **Routes GeoJSON** | All routed stores formatted for external mapping tools |

---

## 7. Routes page

### 7.1 Filters at the top
- **Cluster / rep route / day of week / size tier / coverage status / score** — colouring of dots on the map
- **Rep** — focus on a single rep
- **Month** — view one month of the 2-month plan
- **Date** — view a single working day
- **Show gap stores / Show covered stores** — toggle visibility

### 7.2 Per-rep tables
Each rep shows:
- Total stores assigned
- Visits/month
- Time needed
- Daily breakdown (Mon–Fri × 4 weeks × 2 months)

### 7.3 Downloads
- All reps full-month CSV
- Per-rep CSV
- Uncovered outlets CSV (stores that didn't make it into any route, with exclusion reason)

---

## 8. Recent improvements you can mention in the walkthrough

| Improvement | What it solved |
|---|---|
| **Encoding auto-detect (Asian + Latin)** | Thai/Chinese/Japanese/Korean files no longer break the upload |
| **Mojibake auto-repair** | Excel-round-tripped Brazilian portfolios show `Atacadão` instead of `Atacadão` |
| **CEP / postal code support** | Brazilian addresses geocode at block level instead of city centroid |
| **Cities scrape mode** | State-wide scrapes (Pernambuco, Klang Valley) only cover real cities, not random Selangor neighbours |
| **2 km tiles for big cities** | Recovers ~400 missing stores in Recife where the old 3 km tiles hit Google's 60-result cap |
| **Region filter auto-skip in Cities mode** | Doesn't drop interior PE stores whose vicinity lacks "PE" |
| **`enrichment_attempted` flag** | Re-uploading the enriched portfolio doesn't re-pay for the same dead lookups |
| **Honest actual cost banner** | Post-run report stops faking $14 charges when reality is $0 |
| **Geocode-only mode** | Pure geocoding runs cost only $0.005 × rows missing coords, with immediate download |
| **Chain-name match (Layer 5)** | NSK Trade City / Atacadão branches with 365 m office-vs-storefront offset now correctly tagged covered |
| **Data-aware scoring (NEW)** | Portfolio stores with missing rating/reviews are scored fairly on the signals they DO have |
| **Sales bypass (NEW)** | Top X% of portfolio by annual sales are auto-included in routing — safety net for top revenue accounts |

---

## 9. Common scenarios and what the tool does

### Scenario A: Brand new market, no portfolio
1. Configure → upload empty portfolio template (or skip)
2. Set scrape mode + categories
3. Run Pipeline → scrapes universe, scores, recommends N reps based on opportunity volume

### Scenario B: Existing portfolio, want gap analysis
1. Configure → upload current coverage with sales data
2. Set Store Selection % to 100 (don't lose any portfolio store)
3. Run → output gap list = scraped stores not yet in your portfolio

### Scenario C: Cost-optimised re-run after enrichment
1. First run: pay for scrape + portfolio enrichment
2. Download "enriched portfolio CSV"
3. Future runs: upload that file → enrichment skipped → only geocoding cost (if any new addresses)
4. Tick "Enrich ALL" once to complete the sweep, then every run is $0

### Scenario D: Geocode-only batch
1. Upload portfolio with addresses but no lat/lng
2. Tick "Geocode-only mode"
3. Run → Stage 1 fires, then stops with a download button
4. Cost = $0.005 × rows × $5 per 1000 rows

---

## 10. Quick reference: API costs

| Operation | Cost | When it fires |
|---|---|---|
| Geocode | $0.005/call | Stage 1 only on rows missing lat/lng |
| Google Places Nearby Search | $0.032/call | Stage 2 scrape, per tile, per category |
| Google Place Details | $0.017/call | Stage 7 enrichment for each store with a place_id |
| Google Place Text Search | $0.032/call | Stage 4 portfolio enrichment (capped at 200 unless Enrich-ALL is on) |

---

## 11. Where to find each setting

| If you need to... | Go to... |
|---|---|
| Change scoring weights | Admin Settings → Section 2 |
| Adjust Large/Medium/Small percentile splits | Admin Settings → Section 3 |
| Enable data-aware scoring | Admin Settings → Section 2 → bottom checkbox |
| Set per-category visit playbook | Configure → Visit Playbook tab |
| Add dedicated rep rules | Configure → My Team tab → Dedicated rep rules |
| Exclude direct-served chains | Configure → Direct accounts to exclude |
| Switch between rectangle and cities scrape | Configure → Market Area → Scrape Mode radio |
| Enable sales bypass | Configure → My Team tab → "Always route top portfolio sellers" |
| Skip portfolio enrichment | Run Pipeline → Geocode-only mode checkbox |
| Run all portfolio enrichments in one go | Run Pipeline → Enrich ALL checkbox |
| Replace a corrupt cache with a CSV | Run Pipeline → Replace cache by importing a CSV |
| Repair Latin mojibake in cache | Run Pipeline → "Repair encoding in cache" button |

---

*Last updated alongside PR #49 (data-aware scoring + sales bypass). For questions during the walkthrough, refer to the relevant section number above.*
