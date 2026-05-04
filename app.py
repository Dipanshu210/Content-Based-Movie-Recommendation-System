import pandas as pd
import streamlit as st
import requests

# ---------------- SESSION STATE ----------------
if "watchlist" not in st.session_state:
    st.session_state.watchlist = []

# ---------------- FETCH MOVIE DETAILS ----------------
def fetch_movie_extra_details(movie_id):
    api_key = "8ad39994975564bdd0e701b723e3c4e1"
    base_url = f"https://api.themoviedb.org/3/movie/{movie_id}"

    details = {
        "poster": "https://via.placeholder.com/500x750?text=No+Image",
        "overview": "No description available.",
        "cast": "N/A",
        "rating": 0,
        "vote_count": 0,
        "popularity": 0,
        "trailer": "#"
    }

    try:
        r = requests.get(f"{base_url}?api_key={api_key}&language=en-US", timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("poster_path"):
                details["poster"] = "https://image.tmdb.org/t/p/w500/" + data["poster_path"]

            details["overview"] = data.get("overview", details["overview"])
            details["rating"] = data.get("vote_average", 0)
            details["vote_count"] = data.get("vote_count", 0)
            details["popularity"] = round(data.get("popularity", 0))

        c = requests.get(f"{base_url}/credits?api_key={api_key}", timeout=10)
        if c.status_code == 200:
            cast_list = c.json().get("cast", [])[:3]
            names = [actor["name"] for actor in cast_list]
            if names:
                details["cast"] = ", ".join(names)

        v = requests.get(f"{base_url}/videos?api_key={api_key}", timeout=10)
        if v.status_code == 200:
            for vid in v.json().get("results", []):
                if vid["type"] == "Trailer" and vid["site"] == "YouTube":
                    details["trailer"] = f"https://www.youtube.com/watch?v={vid['key']}"
                    break

    except Exception as e:
        print(e)

    return details

# ---------------- RECOMMENDATION ----------------
def get_recommendations(search_type, value=None):
    results = []

    if search_type == "title":
        idx = movies[movies['title'] == value].index[0]
        distances = similarity[idx]
        recs = sorted(list(enumerate(distances)),
                      reverse=True,
                      key=lambda x: x[1])[1:6]

        for i in recs:
            results.append({
                "title": movies.iloc[i[0]].title,
                "id": movies.iloc[i[0]].movie_id
            })

    elif search_type == "mood":
        filtered = movies[movies['tags'].str.contains(value, case=False, na=False)]
        if not filtered.empty:
            sample = filtered.sample(n=min(5, len(filtered)))
            for _, row in sample.iterrows():
                results.append({
                    "title": row.title,
                    "id": row.movie_id
                })

    elif search_type == "top":
        top = movies.sort_values(by="vote_average", ascending=False).head(5)
        for _, row in top.iterrows():
            results.append({
                "title": row.title,
                "id": row.movie_id
            })

    final = []
    for r in results:
        final.append({
            "title": r["title"],
            "id": r["id"],
            "details": fetch_movie_extra_details(r["id"])
        })

    return final

# ---------------- UI ----------------
st.set_page_config(page_title="Movie App", layout="wide")
st.title("🎥 Movie Recommendation System")

# Load data
try:
    movies = pd.read_pickle("artifacts/movie_list.pkl")
    similarity = pd.read_pickle("artifacts/similarity.pkl")
    movie_titles = movies["title"].values
except:
    st.error("Dataset not found")
    st.stop()

# ---------------- SIDEBAR ----------------
st.sidebar.header("🔎 Search Options")

mode = st.sidebar.radio("Choose Mode", [
    "Standard Search",
    "Mood/Genre",
    "⭐ High Rated"
])

# ---------------- WATCHLIST ----------------
st.sidebar.header("❤️ Watchlist")

if st.session_state.watchlist:
    for i, item in enumerate(st.session_state.watchlist):
        col1, col2 = st.sidebar.columns([3,1])
        col1.write(item["title"])

        if col2.button("❌", key=f"remove_{item['id']}_{i}"):
            st.session_state.watchlist.pop(i)
            st.rerun()
else:
    st.sidebar.write("No movies added")

# ---------------- SEARCH ----------------
recommendations = []

mood_map = {
    "😊 Fun": "Comedy",
    "🔥 Thrilling": "Action",
    "😢 Emotional": "Drama",
    "🌌 Cosmic": "Science Fiction"
}

if mode == "Standard Search":
    selected = st.selectbox("Select Movie", movie_titles)
    if st.button("Recommend"):
        recommendations = get_recommendations("title", selected)

elif mode == "Mood/Genre":
    mood = st.selectbox("Select Mood", list(mood_map.keys()))
    if st.button("Search"):
        recommendations = get_recommendations("mood", mood_map[mood])

elif mode == "⭐ High Rated":
    if st.button("Show Top Movies"):
        recommendations = get_recommendations("top")

# ---------------- DISPLAY ----------------
if recommendations:
    cols = st.columns(5)

    for i, movie in enumerate(recommendations):
        with cols[i]:
            st.image(movie["details"]["poster"])
            st.markdown(f"**{movie['title']}**")
            st.caption(f"⭐ {movie['details']['rating']} | 👥 {movie['details']['vote_count']}")

            # ✅ UNIQUE KEY (CRITICAL FIX)
            key = f"{movie['id']}_{i}_{mode}"

            # ✅ CHECK CORRECTLY
            is_added = any(m["id"] == movie["id"] for m in st.session_state.watchlist)

            if not is_added:
                if st.button("⭐ Add", key=f"add_{key}"):
                    st.session_state.watchlist.append({
                        "id": movie["id"],  # ✅ IMPORTANT FIX
                        "title": movie["title"],
                        "poster": movie["details"]["poster"]
                    })
                    st.rerun()
            else:
                st.button("❤️ Added", key=f"added_{key}", disabled=True)

            # DETAILS
            with st.expander("Details"):
                st.write("🎭 Cast:", movie["details"]["cast"])
                st.write("📝 Overview:", movie["details"]["overview"])
                st.write("📈 Popularity:", movie["details"]["popularity"])
                st.link_button("▶ Trailer", movie["details"]["trailer"])
