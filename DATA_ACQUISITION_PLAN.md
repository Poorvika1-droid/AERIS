# Data Acquisition Plan for AERIS SIH 2026

## Current Situation

**Available Data:**
- NCMRWF forecasts: June 2020 (7 initialization times)
- IMD observations: 2025 (365 days)
- **Problem: No temporal overlap**

## Required Data for Training

### Minimum Viable Dataset (Quick Start)
**Timeline:** 2-4 weeks to acquire

#### Option 1: Match 2020 Forecasts with 2020 Observations
**Required:**
- IMD gridded rainfall observations for June 2020
- Spatial resolution: 0.25° (to match RF25_ind2025_rfp25.nc grid)
- Time period: June 1-30, 2020
- Temporal resolution: Daily

**Source:**
- IMD Data Portal: https://imdpune.gov.in/
- Specifically: "Daily Rainfall Data" or "RF0.25 Gridded Data"
- Contact: IMD Pune (imdpune@imd.gov.in)

**Expected outcome:**
- 7 forecast initialization times
- 20 lead times per initialization
- ~140 forecast-observation pairs
- Sufficient for initial prototyping, NOT for robust model training

#### Option 2: Match 2025 Observations with 2025 Forecasts
**Required:**
- NCMRWF operational forecasts for 2025
- Variables: precipitation, temperature, wind, pressure
- Lead times: 6h to 120h
- Initialization frequency: Daily (00Z and 12Z)

**Source:**
- NCMRWF (National Centre for Medium Range Weather Forecasting)
- Contact: ncmrwf@nic.in
- TIGGE archive: https://confluence.ecmwf.int/display/TIGGE/
- Requires research/academic access agreement

**Expected outcome:**
- Full 2025 overlap with IMD observations
- 365 days of training data
- Better for initial training but still limited temporal diversity

---

### Recommended: Multi-Year Historical Archive (Scientific Best Practice)
**Timeline:** 4-8 weeks to acquire

**Required:**
- 3-5 years of overlapping forecasts and observations
- Suggested period: 2019-2023 (post-monsoon improvements)
- Models: ECMWF, NCMRWF, GFS (at minimum)
- Observations: IMD gridded rainfall, plus station data if available

#### Forecast Sources

**1. ECMWF (European Centre for Medium-Range Weather Forecasts)**
- Data: TIGGE archive
- Variables: tp (precipitation), 2t (temperature), 10u/10v (wind), msl (pressure)
- Resolution: 0.5° or 0.25°
- Access: https://www.ecmwf.int/en/forecasts/datasets/archive-datasets
- Cost: Free for research (registration required)
- Timeline: 1-2 weeks approval + download

**2. NCMRWF (National Centre for Medium Range Weather Forecasting)**
- Data: TIGGE archive or direct request
- Variables: Same as ECMWF
- Resolution: 0.5° or higher
- Access: Contact NCMRWF directly (Indian government agency)
- Cost: Likely free for SIH project
- Timeline: 2-4 weeks approval + data transfer

**3. GFS (Global Forecast System - NOAA)**
- Data: NCEP archive
- Variables: Same as ECMWF
- Resolution: 0.5°
- Access: https://www.ncei.noaa.gov/products/weather-models-global-forecast-system
- Cost: Free
- Timeline: Immediate download

#### Observation Sources

**1. IMD Gridded Rainfall (Primary Target)**
- Data: RF0.25 (0.25° gridded daily rainfall)
- Period: 2019-2023
- Source: https://imdpune.gov.in/
- Access: Requires registration and request
- Cost: Free for research
- Timeline: 2-3 weeks approval

**2. IMD Station Data (Validation)**
- Data: Daily station observations
- Source: Same as above
- Use for point verification and quality control

**3. ERA5 Reanalysis (Context Features)**
- Data: ERA5-Land or ERA5
- Variables: Multiple meteorological fields
- Source: Copernicus Climate Data Store (CDS)
- Access: https://cds.climate.copernicus.eu/
- Cost: Free (registration required)
- Timeline: Immediate download
- **Note:** Classified as REANALYSIS, not used as forecast member

---

## Data Requirements by Priority

### Priority 1: Immediate (for prototype demonstration)
1. **IMD June 2020 rainfall** (matches existing NCMRWF forecasts)
   - Enables: 7 initialization × 20 leads = 140 samples
   - Timeline: 2-3 weeks
   - Use: Initial pipeline testing, leakage validation

### Priority 2: Short-term (for initial model training)
1. **NCMRWF 2025 forecasts** (matches existing IMD 2025 observations)
   - Enables: 365 days of training data
   - Timeline: 3-4 weeks
   - Use: First training iteration, baseline models

### Priority 3: Long-term (for robust production system)
1. **Multi-year archive (2019-2023)**
   - ECMWF + NCMRWF + GFS forecasts
   - IMD gridded observations
   - Enables: 3-5 years training, proper validation, skill assessment
   - Timeline: 6-8 weeks
   - Use: Production model training, comprehensive evaluation

---

## Technical Specifications

### Forecast Data Format
- **Format:** GRIB2 or NetCDF4
- **Dimensions:**
  - init_time (forecast initialization)
  - lead_time (forecast horizon)
  - latitude
  - longitude
- **Required metadata:**
  - model_id
  - initialization_time
  - valid_time
  - lead_hours
  - variable
  - units
  - spatial_resolution

### Observation Data Format
- **Format:** NetCDF4
- **Dimensions:**
  - time (observation time)
  - latitude
  - longitude
- **Required metadata:**
  - source_provider (IMD)
  - observation_time
  - availability_time (when data became available)
  - variable
  - units
  - spatial_resolution

### Common Grid
- **Target grid:** 0.25° (matches IMD RF0.25)
- **Extent:** India region (approx. 5°N-40°N, 65°E-100°E)
- **Regridding method:** Bilinear interpolation for precipitation, conservative for other variables

---

## Action Plan

### Week 1-2: Acquire Priority 1 Data
1. Submit request to IMD for June 2020 RF0.25 data
2. Contact IMD Pune: imdpune@imd.gov.in
3. Cite SIH 2026 project (PS26081)
4. Request: Daily gridded rainfall, June 1-30, 2020, 0.25° resolution

### Week 3-4: Acquire Priority 2 Data
1. Contact NCMRWF for 2025 operational forecasts
2. Request: 2025 forecasts matching IMD observation period
3. Variables: precipitation, temperature, wind, pressure
4. Cite SIH 2026 project

### Week 5-8: Acquire Priority 3 Data
1. Register for ECMWF TIGGE access
2. Download 2019-2023 forecasts
3. Submit IMD request for 2019-2023 gridded data
4. Download GFS from NCEP (free, immediate)
5. Download ERA5 from CDS (free, immediate)

---

## Alternative: Publicly Available Data

If government agencies are slow to respond, consider these alternatives:

### IMD Rainfall Data via Research Platforms
- **India Water Portal:** https://www.indiawaterportal.org/
- **VANDE BHARAT:** Some IMD data available
- **Research papers:** Contact authors who used IMD data

### Open Forecast Data
- **ECMWF Public Datasets:** Limited public access
- **NOAA GFS:** Fully open, immediate download
- **NCEP/NCAR Reanalysis:** Fully open (use as context, not forecast)

---

## Data Storage Requirements

### Estimate for 3-Year Archive
- **Forecasts (3 models × 3 years × 365 days × 4 vars × 0.25° grid):**
  - ~50-100 GB
- **Observations (3 years × 365 days × 1 var × 0.25° grid):**
  - ~5-10 GB
- **Total:** ~55-110 GB

### Storage Location
- `C:\Users\poorv\OneDrive\Desktop\AERIS\data\raw\` - Original downloaded files
- `C:\Users\poorv\OneDrive\Desktop\AERIS\data\processed\` - Harmonized NetCDF files
- `C:\Users\poorv\OneDrive\Desktop\AERIS\data\training\` - Training datasets

---

## Verification Checklist

Before using any data, verify:
- [ ] Provider identity and data source authenticity
- [ ] Temporal coverage matches requirements
- [ ] Spatial coverage includes India region
- [ ] Variable units are documented
- [ ] Initialization/valid time fields are present
- [ ] Data license allows research use
- [ ] No missing periods or gaps
- [ ] Coordinate system is WGS84
- [ ] Timezone is UTC

---

## Contact Templates

### IMD Data Request Email Template
```
Subject: Data Request for Smart India Hackathon 2026 Project PS26081

Dear IMD Data Support Team,

I am working on Smart India Hackathon 2026 project PS26081:
"Hybrid AI–NWP Multi-Model Forecast Blending System"
sponsored by Ministry of Earth Sciences, NCMRWF.

We request access to the following IMD data:
- RF0.25 gridded daily rainfall data
- Period: June 1-30, 2020 (or 2019-2023 if available)
- Spatial resolution: 0.25°
- Format: NetCDF preferred

This data will be used for:
- Training a multi-model forecast blending system
- Academic research and SIH competition
- No commercial use

Please let us know the application process and any required documentation.

Thank you for your support.

[Your Name]
[Your Institution]
[Contact Information]
```

### NCMRWF Forecast Request Email Template
```
Subject: Forecast Data Request for SIH 2026 PS26081

Dear NCMRWF Team,

I am working on Smart India Hackathon 2026 project PS26081:
"Hybrid AI–NWP Multi-Model Forecast Blending System"
sponsored by Ministry of Earth Sciences, NCMRWF.

We request access to the following NCMRWF forecast data:
- Operational forecasts for 2025 (or 2019-2023 historical archive)
- Variables: precipitation, temperature, wind, pressure
- Lead times: 6h to 120h
- Initialization: Daily (00Z and 12Z)
- Format: GRIB2 or NetCDF

This data will be used for:
- Training a dynamic forecast blending system
- Academic research and SIH competition
- No commercial use

As this is an MoES-sponsored project, we request your support in providing
access to the required forecast data.

Thank you for your support.

[Your Name]
[Your Institution]
[Contact Information]
```

---

## Summary

**Critical Path:**
1. ✅ Infrastructure (I will build this now)
2. ⏳ Data acquisition (you must initiate)
3. ⏳ Data processing (when data arrives)
4. ⏳ Model training (after data overlap verified)

**I will now build:**
- Data ingestion adapters
- Temporal alignment pipeline
- Spatial alignment/regridding pipeline
- Quality control pipeline
- Training dataset builder
- All will be ready when you obtain overlapping data
