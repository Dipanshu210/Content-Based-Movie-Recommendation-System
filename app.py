import pandas as pd
import pickle
import streamlit as st
import requests

# --- 1. DATA FETCHING FUNCTION ---
def fetch_movie_extra_details(movie_id):
    """Fetches full movie metadata from TMDB API"""
    api_key = "8ad39994975564bdd0e701b723e3c4e1" # REPLACE WITH YOUR ACTUAL KEY
    base_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    
    try:
        # Fetch Basic Details (Poster, Overview, Rating, Vote Count)
        resp = requests.get(f"{base_url}?api_key={api_key}&language=en-US", timeout=10)
        data = resp.json()
        
        # Fetch Credits (Cast)
        credits_resp = requests.get(f"{base_url}/credits?api_key={api_key}&language=en-US", timeout=10)
        credits_data = credits_resp.json()
        cast = [member['name'] for member in credits_data.get('cast', [])[:3]]
        
        # Fetch Videos (Trailer)
        video_resp = requests.get(f"{base_url}/videos?api_key={api_key}&language=en-US", timeout=10)
        video_data = video_resp.json()
        trailer_link = "https://www.youtube.com/results?search_query=" + data.get('title', '').replace(" ", "+") + "+trailer"
        
        for video in video_data.get('results', []):
            if video['type'] == 'Trailer' and video['site'] == 'YouTube':
                trailer_link = f"https://www.youtube.com/watch?v={video['key']}"
                break
        
        return {
            "poster": "https://image.tmdb.org/t/p/w500/" + str(data.get('poster_path', '')),
            "overview": data.get('overview', 'No description available.'),
            "rating": data.get('vote_average', 'N/A'),
            "release_date": data.get('release_date', 'Unknown'),
            "cast": ", ".join(cast) if cast else "Information unavailable",
            "trailer": trailer_link,
            "vote_count": data.get('vote_count', 0)
        }
    except:
        return {
            "poster": "https://via.placeholder.com/500x750?text=No+Image",
            "overview": "Information unavailable.",
            "rating": "N/A",
            "release_date": "N/A",
            "cast": "N/A",
            "trailer": "#",
            "vote_count": 0
        }

# --- 2. RECOMMENDATION LOGIC ---
def recommend_by_title(movie_title):
    """Classic content-based filtering using similarity matrix"""
    movie_index = movies[movies['title'] == movie_title].index[0]
    distances = similarity[movie_index]
    movie_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]
    
    recs = []
    for i in movie_list:
        movie_id = movies.iloc[i[0]].movie_id
        recs.append({"title": movies.iloc[i[0]].title, "details": fetch_movie_extra_details(movie_id)})
    return recs

def recommend_by_mood(category):
    """Discovery filtering based on tags/genres"""
    mask = movies['tags'].str.contains(category, case=False, na=False)
    filtered = movies[mask]
    # Sample 5 random movies for variety
    samples = filtered.sample(n=min(5, len(filtered)))
    
    recs = []
    for i, row in samples.iterrows():
        recs.append({"title": row.title, "details": fetch_movie_extra_details(row.movie_id)})
    return recs

# --- 3. UI SETUP & DATA LOADING ---
st.set_page_config(page_title="Movie Universe", layout="wide")
st.header("Personalized Movie Recommendation System")

try:
    movies = pd.read_pickle("artifacts/movie_list.pkl")
    similarity = pd.read_pickle("artifacts/similarity.pkl")
    movie_titles = list(movies['title'].values)
except:
    st.error("Error: Artifacts not found.")
    st.stop()

# Persistent state for "More Like This" clicks
if 'current_movie' not in st.session_state:
    st.session_state.current_movie = movie_titles[0]

# --- 4. NAVIGATION & INPUT ---
st.sidebar.title("Navigation")
app_mode = st.sidebar.selectbox("Choose Recommendation Mode:", ["Search Specific Movie", "Explore by Mood/Genre"])

mood_map = {
    "😊 Happy (Comedy)": "Comedy",
    "😢 Sad (Drama)": "Drama",
    "🚀 Adventurous (Action)": "Action",
    "😱 Scared (Horror)": "Horror",
    "🧠 Thoughtful (Sci-Fi)": "Science Fiction"
}

# --- 5. EXECUTION LOGIC ---
results = []

if app_mode == "Search Specific Movie":
    # Sync selectbox with session state for recursive browsing
    curr_idx = movie_titles.index(st.session_state.current_movie)
    selected_movie = st.selectbox("Select a movie you like:", movie_titles, index=curr_idx)
    
    if st.button('Find Similar Movies'):
        st.session_state.current_movie = selected_movie
        results = recommend_by_title(selected_movie)

else:
    selected_mood = st.selectbox("How are you feeling?", list(mood_map.keys()))
    if st.button('Show Mood Matches'):
        results = recommend_by_mood(mood_map[selected_mood])

# --- 6. DISPLAY RESULTS ---
if results:
    cols = st.columns(5)
    for index, movie in enumerate(results):
        with cols[index]:
            st.markdown(f"**{movie['title']}**")
            st.image(movie["details"]["poster"])
            
            # Show Vote Count ("Watched") and Rating
            st.caption(f"👥 {movie['details']['vote_count']:,} watched")
            st.caption(f"⭐ {movie['details']['rating']} Rating")
            
            # Feature: Deep Discovery Button
            if st.button("More like this", key=f"rec_{index}"):
                st.session_state.current_movie = movie['title']
                # Force rerun to switch to Search Mode for this specific movie
                st.rerun()

            with st.expander("Cast & Plot"):
                st.write(f"**Top Cast:** {movie['details']['cast']}")
                st.write(f"**Overview:** {movie['details']['overview']}")
                st.link_button("Watch Trailer", movie['details']['trailer'])