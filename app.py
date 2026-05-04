import pandas as pd
import pickle
import streamlit as st
import requests

# --- SESSION STATE FOR WATCHLIST ---
if "watchlist" not in st.session_state:
    st.session_state.watchlist = []

# --- 1. ENHANCED DATA FETCHING ---
def fetch_movie_extra_details(movie_id):
    api_key = "8ad39994975564bdd0e701b723e3c4e1"
    base_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    
    details = {
        "poster": "https://via.placeholder.com/500x750?text=No+Image",
        "overview": "No description available.",
        "cast": "Information unavailable",
        "rating": 0,
        "vote_count": 0,
        "popularity": 0,
        "review": "No reviews available yet.",
        "trailer": "#"
    }
    
    try:
        resp = requests.get(f"{base_url}?api_key={api_key}&language=en-US", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            details["poster"] = "https://image.tmdb.org/t/p/w500/" + str(data.get('poster_path', ''))
            details["overview"] = data.get('overview', details["overview"])
            details["rating"] = data.get('vote_average', 0)
            details["vote_count"] = data.get('vote_count', 0)
            details["popularity"] = round(data.get('popularity', 0))
        
        credits_resp = requests.get(f"{base_url}/credits?api_key={api_key}", timeout=10)
        if credits_resp.status_code == 200:
            cast_data = credits_resp.json().get('cast', [])
            cast_names = [member['name'] for member in cast_data[:3]]
            if cast_names:
                details["cast"] = ", ".join(cast_names)
        
        rev_resp = requests.get(f"{base_url}/reviews?api_key={api_key}&language=en-US", timeout=10)
        if rev_resp.status_code == 200:
            rev_data = rev_resp.json()
            if rev_data.get('results'):
                details["review"] = rev_data['results'][0].get('content', 'No content.')[:200] + "..."
        
        video_resp = requests.get(f"{base_url}/videos?api_key={api_key}&language=en-US", timeout=10)
        if video_resp.status_code == 200:
            video_data = video_resp.json()
            for video in video_data.get('results', []):
                if video['type'] == 'Trailer' and video['site'] == 'YouTube':
                    details["trailer"] = f"https://www.youtube.com/watch?v={video['key']}"
                    break
                    
    except Exception as e:
        print(f"Error fetching data: {e}")
        
    return details

# --- 2. RECOMMENDATION LOGIC ---
def get_recommendations(search_type, value):
    results = []
    if search_type == "title":
        idx = movies[movies['title'] == value].index[0]
        distances = similarity[idx]
        m_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]
        for i in m_list:
            results.append({"title": movies.iloc[i[0]].title, "id": movies.iloc[i[0]].movie_id})
    elif search_type == "mood":
        mask = movies['tags'].str.contains(value, case=False, na=False)
        filtered = movies[mask]
        if not filtered.empty:
            samples = filtered.sample(n=min(5, len(filtered)))
            for _, row in samples.iterrows():
                results.append({"title": row.title, "id": row.movie_id})
            
    final_recs = []
    for item in results:
        final_recs.append({
            "title": item['title'],
            "id": item['id'],
            "details": fetch_movie_extra_details(item['id'])
        })
    return final_recs

# --- 3. UI SETUP ---
st.set_page_config(page_title="Ultimate Movie Discovery", layout="wide")
st.title("🎥 Movie Recommendation & Analysis System")

try:
    movies = pd.read_pickle("artifacts/movie_list.pkl")
    similarity = pd.read_pickle("artifacts/similarity.pkl")
    movie_titles = list(movies['title'].values)
except Exception as e:
    st.error(f"Error loading artifacts: {e}")
    st.stop()

# --- 4. SIDEBAR ---
st.sidebar.header("🔎 Search Options")
mode = st.sidebar.radio("Search Type", ["Standard Search", "Mood/Genre", "High Rated"])

# --- WATCHLIST UI ---
st.sidebar.header("⭐ Your Watchlist")

if st.session_state.watchlist:
    for i, movie in enumerate(st.session_state.watchlist):
        col1, col2 = st.sidebar.columns([3,1])
        col1.write(movie)
        if col2.button("❌", key=f"remove_{i}"):
            st.session_state.watchlist.remove(movie)
            st.rerun()
else:
    st.sidebar.write("No movies added yet.")

mood_map = {"😊 Fun": "Comedy", "🔥 Thrilling": "Action", "😢 Emotional": "Drama", "🌌 Cosmic": "Science Fiction"}

# --- 5. EXECUTION ---
recommendations = []

if mode == "Standard Search":
    selected = st.selectbox("Select a movie:", movie_titles)
    if st.button("Recommend Similar"):
        recommendations = get_recommendations("title", selected)

elif mode == "Mood/Genre":
    mood = st.selectbox("Current Mood:", list(mood_map.keys()))
    if st.button("Find Matches"):
        recommendations = get_recommendations("mood", mood_map[mood])

elif mode == "High Rated":
    if st.button("Search Top Rated"):
        recommendations = get_recommendations("mood", "")

# --- 6. DISPLAY ---
if recommendations:
    cols = st.columns(5)
    for index, movie in enumerate(recommendations):
        with cols[index]:
            st.image(movie["details"]["poster"])
            st.markdown(f"**{movie['title']}**")
            st.caption(f"⭐ {movie['details']['rating']}/10 | 👥 {movie['details']['vote_count']:,}")

            # --- WATCHLIST BUTTON ---
            if movie['title'] not in st.session_state.watchlist:
                if st.button("⭐ Add", key=f"add_{index}"):
                    st.session_state.watchlist.append(movie['title'])
                    st.success("Added to Watchlist")
            else:
                if st.button("❤️ Added", key=f"added_{index}"):
                    pass

            with st.expander("Analysis & Details"):
                st.write(f"**Top Cast:** {movie['details']['cast']}")
                st.write("**Overview:**")
                st.write(movie['details']['overview'])
                
                st.divider()
                st.write(f"**Popularity Index:** {movie['details']['popularity']}")
                st.write("**User Review Snippet:**")
                st.info(movie['details']['review'])
                st.link_button("Watch Trailer", movie['details']['trailer'])
