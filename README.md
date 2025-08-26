# Streamlit Supabase App

A Streamlit application that connects to Supabase to fetch and display customer profile data.

## Setup

1. Install Hatch (if not already installed):
```bash
pip install hatch
```

2. Create and activate the environment:
```bash
hatch env create
hatch shell
```

3. The environment variables are already configured in `.env` file with your Supabase credentials.

## Running the App

```bash
hatch run dev
```

Or directly with streamlit:
```bash
streamlit run app.py
```

## Features

- ✅ Connects to Supabase using environment variables
- ✅ Fetches data from `customer_profile` table
- ✅ Displays data in an interactive table
- ✅ Shows data overview and statistics
- ✅ Export data to CSV
- ✅ Error handling and connection status

## Environment Variables

The app uses these environment variables (already configured in `.env`):
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_ANON_KEY`: Your Supabase anonymous API key