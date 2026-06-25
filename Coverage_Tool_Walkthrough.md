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

## 12. Logic & Algorithms Reference (for Q&A)

This section explains the actual decision-making rules and formulas behind each step. Keep it handy during the demo to answer *"how does it actually decide X?"* questions.

### 12.1 Geocoding logic (Stage 1)

**Query construction:**
The pipeline builds the query string as `address + district + city + region + postal_code + country` — empty fields are skipped. Postal code is leading for Brazilian addresses (CEP is block-level precise).

**Quality check:**
After receiving coordinates from Google:
1. Read `location_type` → tag as `precise` (ROOFTOP / RANGE_INTERPOLATED), `approximate` (GEOMETRIC_CENTER / APPROXIMATE), or `failed`
2. Compare lat/lng to market bounding box + buffer of 0.5 degrees (~55 km in either direction)
3. If outside → tag `geocode_suspect = True`

**Re-geocoding for suspects:**
For each suspect store, the pipeline retries with alternative query formats (postal code only, city + country, etc.). If the second attempt lands inside the bbox → `geocode_fixed = True`.

**Bogus-coord detection:**
If 3+ portfolio rows share the same lat/lng (e.g. a city centroid filled by a template), those coords are nulled and re-geocoded individually.

---

### 12.2 Scrape tiling logic (Stage 2)

**Tile radius selection — Rectangle mode:**
`smart_tile_radius()` picks the smallest tile radius from `[1, 2, 3, 5, 8, 10, 15, 20, 30, 50] km` such that the total tile count stays under the cap (`MAX_TILES = 1024`). Small markets get 1 km tiles; large state-wide scrapes get 5–10 km tiles.

**Tile radius selection — Cities mode:**
For each selected city, a per-city radius is set from population:

| Population | Coverage radius around city centre |
|---|---|
| 1M+ | 12 km |
| 500k–1M | 8 km |
| 100k–500k | 5 km |
| 30k–100k | 3 km |
| 5k–30k | 2 km |
| Smaller or unknown | 1.5–4 km |

**Tile-spacing inside each city:**
- If any selected city has 100k+ pop → use **2 km tiles** globally (avoids Google's 60-result cap in dense urban areas)
- Otherwise → 3 km tiles (cheaper)

**Tile-anchored scraping inside each city:**
For each tile centre, call Google Places Nearby Search with each scrape category. Paginate up to 3 pages (Google's max = 60 results per query). Stop earlier if no `next_page_token` is returned.

**Filters applied after scrape:**
1. **Relevance filter** — drops obvious non-grocery types (banks, salons, cafés) using whole-word matching against a 60-term exclusion list
2. **Region filter** — keeps stores whose Google `vicinity` field contains the user-supplied region string (skipped automatically in Cities mode)
3. **Direct-accounts filter** — drops scraped stores whose name contains any banner the user listed as direct-served
4. **Foreign-coord filter** — drops stores whose lat/lng fall outside the market bbox

---

### 12.3 Scoring formula (Stage 3)

**Two-group normalisation:**
Portfolio stores and gap (scraped) stores are scored separately, then normalised 0–1 within each group, then combined.

**Portfolio formula (6 signals, default weights):**

```
score_portfolio = 0.20 × rating_normalised
                + 0.25 × reviews_normalised
                + 0.15 × affluence (price_level / 4)
                + 0.15 × poi_count_normalised
                + 0.15 × annual_sales_normalised
                + 0.10 × lines_per_store_normalised
```

**Gap formula (4 signals — no sales/lines because Google doesn't have them):**

```
score_gap = 0.25 × rating + 0.25 × reviews + 0.25 × affluence + 0.25 × poi_count
```

**Per-signal normalisation:**
- `rating_normalised` = `rating / 5`
- `reviews_normalised` = `log(reviews + 1) / log(max_reviews + 1)` (log-scaled to compress outliers)
- `poi_count_normalised` = `log(poi_count + 1) / log(max_poi + 1)`
- `sales_normalised` = `min(1.0, annual_sales_usd / max_sales)`
- `lines_normalised` = `min(1.0, lines_per_store / max_lines)`
- `affluence` = `price_level / 4` if known, otherwise 0.5

**Final scaling:**
Raw score (0–1) × 100 → integer 0–100.

**Optional: Data-aware scoring (Admin Settings checkbox, default OFF)**
When ON, portfolio stores with missing rating/reviews have those weights redistributed proportionally to signals that ARE present. Example:

- A store has only `sales` and `lines` present → those carry the full weight
- Normal weights: sales 15% + lines 10% = 25% of formula
- Data-aware weights: sales 60% + lines 40% = 100% of formula (renormalised)

Prevents top-selling portfolio stores invisible to Google from scoring < 25/100.

---

### 12.4 Coverage matching logic (Stage 4)

For each scraped store, check these 5 layers in order — first hit wins:

| Layer | Rule | Confidence |
|---|---|---|
| **1. place_id** | Scraped `place_id` == any portfolio `place_id` | High |
| **2. Exact coords** | Rounded lat/lng (≈11 m precision) matches a portfolio row | High |
| **3. Base radius** | Distance ≤ base_radius from a portfolio store | Medium |
| **4. Fuzzy radius + name** | Distance ≤ fuzzy_radius AND bigram name similarity ≥ 0.75 | Medium |
| **5. Chain name** | Distance ≤ 500 m AND bigram name similarity ≥ 0.85 | Medium |

**Base / fuzzy radii by size tier (Stage 4 doesn't know tier yet, so it inspects the scraped store's name for chain keywords):**

| Size tier | Base radius | Fuzzy radius |
|---|---|---|
| Large (hypermarket / known chain) | 200 m | 250 m |
| Medium (supermarket) | 100 m | 150 m |
| Small / Occasional / Unknown | 50 m | 100 m |

**Known chain keywords** (use Large radii regardless of tier): Carrefour, Tesco, Lotus, Lulu, Spinneys, Waitrose, Giant, AEON, NSK, Mydin, Econsave, KK Mart, 99 Speedmart, TF Value, KIP Mart, Atacadão, Assaí, Pão de Açúcar, Walmart, Bompreço, BIG, Atacarejo, Costco, plus generic words `hypermarket`, `hyper`, `mall`, `centre`, `center`.

**Bigram name similarity:**
Strip noise words (`supermercado`, `super`, `mercado`, `LTDA`, `Sdn Bhd`, `Sdn`, `Bhd`, `Enterprise`, `Trading`, etc.). Convert both names to character bigrams (overlapping pairs of letters). Similarity = `|intersection| / |union|`. A perfect match = 1.0; threshold 0.75 means stores like "Pasar Mini Sri Rama" vs "PASAR MINI SRI RAAMA" match.

**Layer 5 specifically:** catches chain stores where the portfolio has the office/registration address but Google has the storefront pin — they can be 300–500 m apart geographically but have nearly identical names. The 0.85 threshold is strict enough to reject shop-in-shop tenants (e.g. MIXUE inside an NSK building, which has similarity ~0.5).

---

### 12.5 Size tier assignment logic (Stage 5)

**Two-path assignment:**

**Path 1 — Sales percentile (portfolio with sales data):**
```
For each portfolio store with annual_sales_usd > 0:
    Calculate the store's sales rank within its category
    If rank percentile >= 100 - large_pct (default 20):
        tier = Large
    elif rank percentile >= 100 - large_pct - medium_pct (default 40):
        tier = Medium
    else:
        tier = Small
```

**Path 2 — Score percentile (everything else: scraped + portfolio without sales):**
Same percentile rule but applied to `score` instead of `annual_sales_usd`.

**Default percentile splits:** Large = top 20%, Medium = middle 40%, Small = bottom 40%. Settable in Admin Settings.

**Why two paths:** sales is a stronger signal than Google score. A real top-seller without Google data would get a low score percentile but is correctly Large by sales percentile.

**Per-category logic:** percentiles are calculated within each category separately (so a top-20% pharmacy is Large regardless of how it compares to supermarkets).

**Per-category visit benchmark:** each tier × category combination has its own visits/month + duration from the Visit Playbook.

---

### 12.6 Rep planning logic (Stage 6)

**Capacity calculation:**

```
effective_daily_minutes = daily_working_minutes - break_minutes
                       = 480 - 30 = 450 min/day (default)
monthly_capacity_per_rep = effective_daily × working_days
                         = 450 × 22 = 9,900 min/month
```

**Time needed per store:**

```
time_per_store_per_month = visits_per_month × (visit_duration + average_travel)
average_travel = depends on territory geographic density
```

**Recommended mode (rep count calculation):**

```
priority_stores = top N% of (portfolio + gap by normalised score)
total_minutes_needed = sum(time_per_store_per_month for priority_stores)
recommended_reps = ceil(total_minutes_needed / (monthly_capacity_per_rep × 0.65))
```

The `0.65` factor targets ~65% utilisation — leaves headroom for traffic, sick days, training, admin. If you wanted 100% utilisation (unrealistic), divide by 1.0 instead.

**Fixed mode (your rep count + cram to fit):**

```
total_capacity = rep_count × monthly_capacity_per_rep
priority_stores = sorted(all stores by score, descending)
keep_in_route = []
running_minutes = 0
for store in priority_stores:
    if running_minutes + time_per_store(store) <= total_capacity:
        keep_in_route.append(store)
        running_minutes += time_per_store(store)
# everything beyond the cap is dropped
```

**Optional: Sales bypass (Configure checkbox)**
When ON, after the priority cut completes, the top X% of portfolio by `annual_sales_usd` are auto-appended to the kept set even if they were below the score cut.

---

### 12.7 Geographic clustering logic (Stage 6 continued)

**Initial k-means clustering:**
- Number of clusters = `recommended_reps` (Recommended mode) or `rep_count` (Fixed)
- Cluster stores by (lat, lng) using k-means
- Each cluster becomes one rep's territory

**Capacitated balancing (3 refinement rounds):**
After k-means, some clusters may be overloaded (too many minutes for one rep) while others are under-utilised. Each refinement round:
1. Identify the most overloaded cluster
2. Find the most under-utilised neighbour cluster
3. Move the geographically closest border stores from overloaded → under-utilised until both are within 15% of average
4. Recompute centroids
5. Repeat up to 3 rounds

**Overload split (Recommended mode only):**
If after balancing any cluster still exceeds 110% utilisation:
- Split the overloaded cluster into 2 sub-clusters (k-means with k=2 on its stores)
- One sub-cluster keeps the existing rep_id; the other gets a new rep_id
- Repeat until no cluster exceeds 110%

**Daily breakdown (final step):**
For each rep's territory:
- Stores are assigned to one of the working days within the plan period (Mon–Fri only). With the default 1-month plan that's 22 working days; if the plan stretches to 2 or 3 months it's 22 × plan_period_months.
- The day-assignment algorithm uses geographic clustering again (k-means with k = working_days_in_plan) so each day's stores are spatially clumped.
- Within each day, stores are visit-ordered using **nearest-neighbour route sort** starting from the cluster centroid.

---

### 12.8 Visit-frequency math

**Plan period is dynamic — driven by the smallest visit frequency in your Visit Playbook:**

```
min_freq    = smallest visits_per_month across the stores in this run
plan_period = max(1, round(1 / min_freq)) if min_freq < 1 else 1
```

| Smallest frequency in the run | plan_period |
|---|---|
| ≥ 1 / month (default — every tier visited at least monthly) | **1 month** |
| 0.5 / month (some tier visited every 2 months) | 2 months |
| 0.33 / month (some tier visited every 3 months) | 3 months |

So out of the box the plan is **1 month**. It only stretches when you edit the Visit Playbook to give a tier a sub-monthly frequency (e.g. Occasional = 0.5/mo). The status line in Stage 6b prints `Building {plan_period}-month route plan…` so you can always see which value applied.

**Plan visits per store:**
```
plan_visits = round(visits_per_month × plan_period)
```

Examples with **plan_period = 1** (default):
- Large at 4 visits/month → 4 plan visits.
- Medium at 2 visits/month → 2 plan visits.
- Small at 1 visit/month → 1 plan visit.

Examples with **plan_period = 2** (only if a tier is set to 0.5/mo):
- Large at 4 visits/month → 8 plan visits across 2 months.
- Occasional at 0.5 visit/month → 1 plan visit across 2 months.

**Date assignment:**
For each store, the pipeline picks specific calendar dates within the plan period so that:
- Visits are evenly spaced (e.g. weekly visits land on the same weekday)
- Visits don't fall on weekends (Sat/Sun excluded)
- Public holidays are skipped if a holiday list is supplied

---

### 12.9 Utilisation calculation

**Per-rep utilisation:**
```
rep_utilisation = (time_needed_per_month / monthly_capacity_per_rep) × 100
```

**Targets (Recommended mode):**
- < 60% → flagged "under-utilised", may merge with neighbour
- 60–85% → healthy
- 85–110% → tight, no slack
- > 110% → overloaded, triggers split

**Fixed mode:**
Utilisation can hit 100% by design (cram-to-fit). No split. Stores beyond capacity are simply dropped.

---

### 12.10 Encoding detection logic (CSV upload)

The pipeline tries encodings in this exact order until one succeeds without raising UnicodeDecodeError:

1. `utf-8`
2. `utf-8-sig` (UTF-8 with BOM)
3. `cp874`, `tis-620` (Thai)
4. `gbk`, `gb18030`, `big5` (Chinese)
5. `cp932`, `shift_jis` (Japanese)
6. `cp949`, `euc-kr` (Korean)
7. `cp1256` (Arabic)
8. `latin-1`, `cp1252`, `iso-8859-1` (Latin, last resort — these never raise, so they catch anything)

**Mojibake auto-repair:**
After successful read, scans every string cell for `Ã` or `Â` markers (signature of UTF-8 read as Latin-1). For any cell with these:
- Try `text.encode("latin-1").decode("utf-8")` — reverses the damage
- Keep the result only if it strictly reduces the `Ã`/`Â` count
- Clean text is left untouched

---

### 12.11 Cost estimation logic

**Pre-run estimate (banner at top of Run Pipeline):**

```
geocode_cost = (rows missing valid lat/lng) × $0.005
enrich_cost  = min(200, rows missing rating AND not in session cache) × $0.032
total_estimate = geocode_cost + enrich_cost
```

The cap of 200 disappears if Enrich-ALL is ticked.

**Post-run actual cost:**
```
real_geocode_calls    = actual length of needs_geocode at runtime
real_portfolio_enrich = actual length of _need_fetch at runtime
universe_scrape_cost  = 0 if cache used, else (len(universe) / 15) × $0.032
stage7_details_cost   = enriched_count × $0.017 only if Stage 7 actually ran

actual_cost = (real_geocode × $0.005)
            + (real_portfolio_enrich × $0.032)
            + universe_scrape_cost
            + (stage7_details × $0.017)
```

The previous broken formula multiplied `len(portfolio) × $0.005` (charging for skipped rows) and `len(universe)/15 × $0.032` (charging for cached scrapes that didn't fire). This was the source of "actual cost ~$14" reports when reality was $0–$6.

---

### 12.12 Constants you can reference during Q&A

| Constant | Value | Where it lives |
|---|---|---|
| MAX_TILES | 1024 | Stage 2 scrape grid cap |
| PRICE_NEARBY_PER_CALL | $0.032 | Google Places Nearby Search + Text Search |
| PRICE_GEOCODE_PER_CALL | $0.005 | Geocoding API |
| PRICE_DETAILS_PER_CALL | $0.017 | Google Place Details |
| Default rating weight (portfolio) | 20% | Stage 3 |
| Default reviews weight (portfolio) | 25% | Stage 3 |
| Default sales weight (portfolio) | 15% | Stage 3 |
| Bigram similarity threshold (Layer 4) | 0.75 | Stage 4 |
| Chain bigram similarity threshold (Layer 5) | 0.85 | Stage 4 |
| Chain max distance (Layer 5) | 500 m | Stage 4 |
| Default Large size percentile | top 20% | Stage 5 |
| Default Medium size percentile | next 40% | Stage 5 |
| Effective daily minutes | 450 min (480 - 30 break) | Stage 6 |
| Capacitated balancing rounds | 3 | Stage 6 |
| Overload split threshold | 110% | Stage 6 |
| Plan period | 2 months | Stage 8 |
| Stage 4 portfolio enrichment cap | 200 (or unlimited with Enrich-ALL) | Stage 4 |

---

## 13. FAQ for the walkthrough

**Q: Why isn't every portfolio store guaranteed a route?**
A: Recommended mode applies a Top N% priority cut by score. Portfolio competes with gap stores in the same ranking. If a portfolio store's score is low (often because rating/reviews are missing from Google), it falls below the cut. Solutions: turn on data-aware scoring, turn on sales bypass, raise Store Selection % to 100, or add reps.

**Q: Why does the same chain appear twice in the universe (once portfolio, once gap)?**
A: The 5-layer matcher in Stage 4 didn't connect them. Usually because:
- Different `place_id` between portfolio and scrape (your portfolio has no place_id field at all)
- Coordinates more than 200 m apart (portfolio has registration address, Google has storefront pin)
- Name similarity below threshold

The new Layer 5 (chain name, similarity ≥ 0.85, distance ≤ 500 m) was added to fix exactly this case for chains like NSK, Atacadão, etc.

**Q: Why is my Recife scrape returning 2,000 stores when I expected 3,500+?**
A: Default 3 km tiles hit Google's 60-result cap in dense areas — invisible silent drop. Cities mode with 2 km tiles fixes this (auto-applied when any selected city has 100k+ population).

**Q: Why does Streamlit lose my categories after I close the app?**
A: Session state is wiped on restart. Save Configuration → download JSON → upload it back next session to restore everything.

**Q: Why is the actual cost not matching the estimate?**
A: After PR #37 the formulas align. If you still see drift, check:
- Did Stage 7 enrichment fire (only when cache was missing)?
- Were there suspect re-geocodes triggered by bad input coords?
- Both will show as a separate status line during the run.

**Q: Can the same rep cover stores in multiple of the 12 Klang Valley areas?**
A: Yes. A rep's territory is geographic, not administrative. They may have 40 stores in Petaling Jaya and a few in Subang Jaya — they count as PJ's primary rep but show up under both areas in the "reps touching" column.

**Q: Why does the tool target 65% rep utilisation by default in Recommended mode?**
A: Real-world reps lose ~25–35% of their planned capacity to traffic, sick days, training, admin, KPI meetings, customer wait times. 65% planned utilisation leaves room for these without missing visits. 100% utilisation is a fantasy that leads to coverage failure and rep burnout.

---


*Last updated alongside PR #49 (data-aware scoring + sales bypass). For questions during the walkthrough, refer to the relevant section number above.*
