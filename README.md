# Doi Saket Weather Dashboard

A production-ready weather monitoring system for Doi Saket, Thailand, featuring automated data collection, MongoDB storage, and Grafana visualization.

## Features

- **Weather Data Collection**: Automated fetching from Weather Underground API with a Personal Weather Station (PWS)
- **Data Enrichment**: Calculates derived metrics like Heat Index, Wet Bulb Temperature, and Fire Danger Index
- **MongoDB Storage**: Stores all data in MongoDB Atlas (free tier compatible)
- **Beautiful Dashboards**: Pre-configured Grafana dashboards with Thai/English labels
- **Docker Support**: One-command setup with Docker Compose
- **Cloud Deployment**: Ready-to-deploy configuration for Render.com

## Quick Start (2 Minutes)

1. **Clone the repository**

```bash
git clone https://github.com/visarutforthaipbs/doi-saket-weather-dashboard.git
cd doi-saket-weather-dashboard
```

2. **Set up environment variables**

```bash
cp .env.sample .env
```

Edit the `.env` file and add:
- Your Weather Underground API key
- MongoDB Atlas connection string (from your free M0 cluster)

3. **Install Python dependencies**

```bash
pip install -r fetcher/requirements.txt
```

4. **Run the weather fetcher**

```bash
python fetcher/weather_fetcher.py
```

5. **Start Grafana (in a separate terminal)**

```bash
cd docker
docker-compose up
```

6. **Access your dashboard**

Open [http://localhost:3000](http://localhost:3000) in your browser
- Username: `admin`
- Password: `admin` (you'll be prompted to change on first login)

## Rendered Metrics

The system calculates and stores these derived weather metrics:

- **Heat Index**: Apparent temperature adjusted for humidity (Rothfusz formula)
- **Wet Bulb Temperature**: Temperature read by a thermometer with a wet wick (Stull formula)
- **Fuel Moisture Index (FMI)**: Estimate of moisture content in materials that could fuel a fire
- **Fire Danger Index**: A measure of fire risk based on wind speed and FMI
- **Pressure Trend**: Barometric pressure change over 3 hours

## Deploying to Render (Free Tier)

### 1. Create a Cron Job on Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New" and select "Cron Job"
3. Connect your GitHub repository
4. Configure:
   - **Name**: `doi-saket-weather-fetcher`
   - **Command**: `python fetcher/weather_fetcher.py`
   - **Schedule**: `*/5 * * * *` (every 5 minutes)
   - Add environment variables from your `.env` file

### 2. Optional: Deploy Grafana (Web Service)

If you want to host the dashboard on Render as well:

1. Click "New" and select "Web Service"
2. Configure:
   - **Name**: `doi-saket-weather-dashboard`
   - **Dockerfile Path**: `docker/Dockerfile`
   - Add the same environment variables

### 3. CI/CD with GitHub Actions

This repo includes a GitHub Actions workflow that can automatically deploy to Render whenever you push to the main branch.

To set it up:
1. Go to your GitHub repository settings
2. Add these secrets:
   - `RENDER_API_KEY`: Your Render API key
   - `RENDER_CRON_SERVICE_ID`: The ID of your cron job service
   - `RENDER_GRAFANA_SERVICE_ID`: (Optional) The ID of your Grafana web service
   - `DEPLOY_GRAFANA`: Set to `true` if you want to deploy Grafana as well

## Security Notes

- **Never commit your real `.env` file**. It's already in `.gitignore`.
- If you accidentally commit API keys or credentials, rotate them immediately.
- MongoDB passwords with special characters must be URL-encoded.

## Dashboard Usage Guide (ข้อมูลการใช้งานแดชบอร์ด)

### ระดับความเสี่ยงความร้อน (Heat Risk Levels)

- 🟢 **Comfort (สบาย)**: < 27°C
- 🟡 **Caution (ระวัง)**: 27-32°C
- 🟠 **Extreme (ร้อนจัด)**: 32-41°C
- 🔴 **Danger (อันตราย)**: > 41°C

### ระดับความเสี่ยงไฟป่า (Fire Risk Levels)

- 🟢 **Low (ต่ำ)**: < 5
- 🟡 **Moderate (ปานกลาง)**: 5-15
- 🔴 **High (สูง)**: > 15

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.