import re
import streamlit as st
import streamlit.components.v1 as components
import instaloader
import anthropic

# ── Italian food backgrounds (Unsplash) ────────────────────────────────────────
ITALIAN_IMAGES = [
    "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?auto=format&fit=crop&w=1920&q=80",  # pizza
    "https://images.unsplash.com/photo-1555949258-eb67b1ef0ceb?auto=format&fit=crop&w=1920&q=80",  # pasta
    "https://images.unsplash.com/photo-1574894709920-11b28e7367e3?auto=format&fit=crop&w=1920&q=80",  # lasagna
    "https://images.unsplash.com/photo-1476124369491-e7addf5db371?auto=format&fit=crop&w=1920&q=80",  # risotto
    "https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?auto=format&fit=crop&w=1920&q=80",  # tiramisu
    "https://images.unsplash.com/photo-1595295333158-4742f28fbd85?auto=format&fit=crop&w=1920&q=80",  # pizza margherita
    "https://images.unsplash.com/photo-1551183053-bf91798d82fc?auto=format&fit=crop&w=1920&q=80",  # spaghetti
]

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Insta Shopping List", page_icon="🛒", layout="centered")

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Hide default Streamlit chrome */
#MainMenu, footer { visibility: hidden; }

/* App background */
.stApp {
    background-size: cover !important;
    background-position: center center !important;
    background-attachment: fixed !important;
}

/* Dark overlay behind everything */
.stApp::before {
    content: "";
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
    z-index: 0;
    pointer-events: none;
}

/* Main content card */
.block-container {
    position: relative;
    z-index: 1;
    background: rgba(255, 255, 255, 0.94) !important;
    border-radius: 20px !important;
    padding: 2.5rem 3rem !important;
    backdrop-filter: blur(14px) !important;
    -webkit-backdrop-filter: blur(14px) !important;
    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.35) !important;
    margin-top: 2.5rem !important;
    margin-bottom: 2.5rem !important;
    max-width: 760px !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    position: relative;
    z-index: 1;
    background: rgba(255, 255, 255, 0.96) !important;
    backdrop-filter: blur(14px) !important;
    -webkit-backdrop-filter: blur(14px) !important;
}

/* Title */
h1 {
    font-size: 2.2rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.5px !important;
    color: #111 !important;
}

/* Subheader */
h3 {
    color: #222 !important;
    font-weight: 700 !important;
}

/* Primary button */
.stButton > button[kind="primary"] {
    background: #e63946 !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 0.6rem 2rem !important;
    transition: background 0.2s ease, transform 0.15s ease, box-shadow 0.2s ease !important;
    color: white !important;
}
.stButton > button[kind="primary"]:hover:not(:disabled) {
    background: #c1121f !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 18px rgba(230, 57, 70, 0.45) !important;
}
.stButton > button[kind="primary"]:disabled {
    opacity: 0.45 !important;
}

/* Text area */
.stTextArea textarea {
    border-radius: 10px !important;
    border: 2px solid #e0e0e0 !important;
    font-size: 0.9rem !important;
    transition: border-color 0.2s ease !important;
}
.stTextArea textarea:focus {
    border-color: #e63946 !important;
    box-shadow: 0 0 0 3px rgba(230, 57, 70, 0.12) !important;
}

/* Download button */
.stDownloadButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
}

/* Responsive: shrink padding on small screens */
@media (max-width: 640px) {
    .block-container {
        padding: 1.5rem 1.2rem !important;
        margin-top: 1rem !important;
        border-radius: 14px !important;
    }
    h1 { font-size: 1.6rem !important; }
}
</style>
""", unsafe_allow_html=True)

# ── Rotating background (JS via iframe → parent document) ──────────────────────
images_json = str(ITALIAN_IMAGES).replace("'", '"')
components.html(f"""
<script>
(function() {{
    const images = {images_json};
    let idx = Math.floor(Math.random() * images.length);

    function applyBg() {{
        const app = window.parent.document.querySelector('.stApp');
        if (app) {{
            app.style.backgroundImage = 'url(' + images[idx] + ')';
        }}
        idx = (idx + 1) % images.length;
    }}

    applyBg();
    setInterval(applyBg, 30000);
}})();
</script>
""", height=0)

# ── Title ──────────────────────────────────────────────────────────────────────
st.title("🛒 Insta Shopping List")
st.caption("Paste Instagram cooking video URLs and get a combined grocery list.")

# ── Sidebar: API key ───────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Setup")
    api_key = st.text_input(
        "Claude API Key",
        type="password",
        placeholder="sk-ant-...",
        help="Get a free key at console.anthropic.com",
    )
    if not api_key:
        st.info("Enter your Claude API key to get started.")

# ── Helpers ────────────────────────────────────────────────────────────────────

def extract_shortcode(url: str) -> str:
    match = re.search(r"/(?:p|reel|tv)/([A-Za-z0-9_-]+)", url)
    if not match:
        raise ValueError(f"Couldn't parse URL: {url}")
    return match.group(1)


def fetch_caption(shortcode: str) -> str:
    L = instaloader.Instaloader(
        quiet=True,
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        save_metadata=False,
    )
    post = instaloader.Post.from_shortcode(L.context, shortcode)
    return post.caption or ""


def looks_like_recipe(caption: str) -> bool:
    keywords = ["cup", "tbsp", "tsp", "gram", "g ", "ml", "oz", "lb",
                "ingredient", "salt", "pepper", "oil", "flour", "butter",
                "egg", "garlic", "onion", "tomato", "chicken", "beef", "sugar"]
    return any(kw in caption.lower() for kw in keywords)


def extract_ingredients_with_claude(captions: list[str], api_key: str) -> str:
    client = anthropic.Anthropic(api_key=api_key)
    numbered = "\n\n---\n\n".join(
        f"Recipe {i + 1}:\n{caption}" for i, caption in enumerate(captions)
    )
    prompt = f"""You are a helpful assistant that extracts grocery ingredients from recipe text.

Given the recipes below, produce a single consolidated shopping list:
- Extract only ingredients (not equipment, steps, or garnishes)
- Skip everyday household staples: water, stock, salt, pepper, and herb/spice powders (e.g. garlic powder, onion powder, paprika)
- Merge duplicates — if multiple recipes need the same item, list it once
- List the ingredient name only — no amounts, quantities, or units
- Translate everything to English — the recipes may be in any language
- Output ONLY a plain bullet list (• item), no headings, no preamble

Recipes:
{numbered}"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


# ── Main UI ────────────────────────────────────────────────────────────────────

urls_input = st.text_area(
    "Instagram URLs (one per line)",
    placeholder="https://www.instagram.com/reel/ABC123/\nhttps://www.instagram.com/reel/DEF456/",
    height=160,
)

generate = st.button(
    "Generate Shopping List",
    type="primary",
    disabled=not (api_key and urls_input.strip()),
)

if generate:
    urls = [u.strip() for u in urls_input.splitlines() if u.strip()]
    captions = []
    warnings = []

    with st.status("Fetching posts from Instagram…", expanded=True) as status:
        for url in urls:
            try:
                shortcode = extract_shortcode(url)
                caption = fetch_caption(shortcode)
                if not caption:
                    warnings.append(f"⚠️ No caption found for: {url}")
                elif not looks_like_recipe(caption):
                    warnings.append(f"⚠️ Caption may not contain ingredients: {url}")
                    captions.append(caption)
                else:
                    captions.append(caption)
                    st.write(f"✅ {url}")
            except ValueError as e:
                st.write(f"❌ Bad URL — {e}")
            except Exception as e:
                st.write(f"❌ Couldn't fetch {url} — {e}")
        status.update(label="Done fetching!", state="complete")

    for w in warnings:
        st.warning(w)

    if not captions:
        st.error("No usable captions found. Make sure the posts are public and contain recipe text.")
        st.stop()

    with st.spinner("Extracting ingredients with Claude…"):
        try:
            shopping_list = extract_ingredients_with_claude(captions, api_key)
        except anthropic.AuthenticationError:
            st.error("Invalid Claude API key. Check it in the sidebar.")
            st.stop()
        except Exception as e:
            st.error(f"Claude API error: {e}")
            st.stop()

    st.divider()
    st.subheader("🛒 Your Shopping List")
    st.markdown(shopping_list)

    st.download_button(
        label="📥 Download as .txt",
        data=shopping_list,
        file_name="shopping_list.txt",
        mime="text/plain",
    )
