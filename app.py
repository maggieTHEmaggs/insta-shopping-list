import re
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
import instaloader
import anthropic

# ── Household basics (persistent) ─────────────────────────────────────────────
BASICS_FILE = Path(__file__).parent / "basics.txt"

DEFAULT_BASICS = """water
salt
pepper
olive oil
vegetable stock
chicken stock
garlic powder
onion powder
paprika
cumin
oregano
sugar
flour"""

def load_basics() -> str:
    if BASICS_FILE.exists():
        return BASICS_FILE.read_text(encoding="utf-8").strip()
    return DEFAULT_BASICS

def save_basics(text: str) -> None:
    BASICS_FILE.write_text(text.strip(), encoding="utf-8")

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
#MainMenu, footer, [data-testid="stSidebar"] { display: none !important; }

/* Background */
.stApp {
    background-size: cover !important;
    background-position: center center !important;
    background-attachment: fixed !important;
}

/* Dark overlay */
.stApp::before {
    content: "";
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.55);
    z-index: 0;
    pointer-events: none;
}

/* Glass card */
.block-container {
    position: relative;
    z-index: 1;
    background: rgba(255, 255, 255, 0.08) !important;
    border: 1px solid rgba(255, 255, 255, 0.18) !important;
    border-radius: 24px !important;
    padding: 2.5rem 3rem !important;
    backdrop-filter: blur(28px) !important;
    -webkit-backdrop-filter: blur(28px) !important;
    box-shadow: 0 16px 56px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255,255,255,0.15) !important;
    margin-top: 2.5rem !important;
    margin-bottom: 2.5rem !important;
    max-width: 780px !important;
}

/* All text white — scoped to headings, labels, paragraphs */
.block-container h1,
.block-container h2,
.block-container h3,
.block-container p,
.block-container label,
.block-container .stMarkdown p,
.block-container .stCaption { color: white !important; }

/* Secondary / save buttons: dark text */
.stButton > button:not([kind="primary"]) {
    color: #111 !important;
    background: rgba(255, 255, 255, 0.85) !important;
    border: 1px solid rgba(255, 255, 255, 0.4) !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
}

/* Title */
h1 {
    font-size: 2.2rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.5px !important;
}

/* Expander (API key) */
.streamlit-expanderHeader {
    background: rgba(255, 255, 255, 0.1) !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    border-radius: 12px !important;
    color: white !important;
    font-weight: 600 !important;
}
.streamlit-expanderHeader:hover {
    background: rgba(255, 255, 255, 0.15) !important;
}
.streamlit-expanderContent {
    background: rgba(255, 255, 255, 0.06) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-top: none !important;
    border-radius: 0 0 12px 12px !important;
    padding: 1rem !important;
}

/* Inputs — light background, dark text for readability */
.stTextArea textarea,
.stTextInput input {
    background: rgba(255, 255, 255, 0.88) !important;
    border: 1px solid rgba(255, 255, 255, 0.4) !important;
    border-radius: 12px !important;
    color: #111 !important;
    font-size: 0.92rem !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextArea textarea::placeholder,
.stTextInput input::placeholder { color: #999 !important; }
.stTextArea textarea:focus,
.stTextInput input:focus {
    border-color: rgba(255,255,255,0.7) !important;
    box-shadow: 0 0 0 3px rgba(255,255,255,0.2) !important;
}

/* Primary button */
.stButton > button[kind="primary"] {
    background: #e63946 !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 0.65rem 2.2rem !important;
    color: white !important;
    transition: background 0.2s, transform 0.15s, box-shadow 0.2s !important;
}
.stButton > button[kind="primary"]:hover:not(:disabled) {
    background: #c1121f !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(230, 57, 70, 0.5) !important;
}
.stButton > button[kind="primary"]:disabled { opacity: 0.4 !important; }

/* Download button */
.stDownloadButton > button {
    background: rgba(255,255,255,0.12) !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    border-radius: 12px !important;
    color: white !important;
    font-weight: 600 !important;
    transition: background 0.2s !important;
}
.stDownloadButton > button:hover {
    background: rgba(255,255,255,0.2) !important;
}

/* Divider */
hr { border-color: rgba(255,255,255,0.15) !important; }

/* Responsive */
@media (max-width: 640px) {
    .block-container {
        padding: 1.5rem 1.2rem !important;
        margin-top: 1rem !important;
        border-radius: 16px !important;
    }
    h1 { font-size: 1.6rem !important; }
}
</style>
""", unsafe_allow_html=True)

# ── Rotating background ────────────────────────────────────────────────────────
images_json = str(ITALIAN_IMAGES).replace("'", '"')
components.html(f"""
<script>
(function() {{
    const images = {images_json};
    let idx = Math.floor(Math.random() * images.length);
    function applyBg() {{
        const app = window.parent.document.querySelector('.stApp');
        if (app) app.style.backgroundImage = 'url(' + images[idx] + ')';
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

# ── Collapsible API key ────────────────────────────────────────────────────────
with st.expander("⚙️ Setup — Claude API Key", expanded=False):
    api_key = st.text_input(
        "Claude API Key",
        type="password",
        placeholder="sk-ant-...",
        help="Get a free key at console.anthropic.com",
    )
    if not api_key:
        st.caption("You need a Claude API key to generate the shopping list. [Get one here](https://console.anthropic.com)")
    else:
        st.caption("✅ API key set.")

# ── Household basics editor ────────────────────────────────────────────────────
with st.expander("🚫 Household Basics — never add to shopping list", expanded=False):
    basics_text = st.text_area(
        "One item per line — these will never appear in your shopping list",
        value=load_basics(),
        height=220,
        key="basics_editor",
    )
    if st.button("💾 Save basics list"):
        save_basics(basics_text)
        st.success("Saved!")

basics_list = [line.strip().lower() for line in basics_text.splitlines() if line.strip()]

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


def extract_ingredients_with_claude(captions: list[str], api_key: str, basics: list[str]) -> str:
    client = anthropic.Anthropic(api_key=api_key)
    numbered = "\n\n---\n\n".join(
        f"Recipe {i + 1}:\n{caption}" for i, caption in enumerate(captions)
    )
    basics_block = "\n".join(f"- {item}" for item in basics) if basics else "(none)"
    prompt = f"""You are a helpful assistant that extracts grocery ingredients from recipe text.

Given the recipes below, produce a single consolidated shopping list:
- Extract only ingredients (not equipment, steps, or garnishes)
- NEVER include any item from the household basics list below — not even partial matches
- Merge duplicates — if multiple recipes need the same item, list it once
- List the ingredient name only — no amounts, quantities, or units
- Translate everything to English — the recipes may be in any language
- Output ONLY a plain bullet list (• item), no headings, no preamble

Household basics to always exclude:
{basics_block}

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
    disabled=not (api_key and urls_input.strip()) if 'api_key' in dir() else True,
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
            shopping_list = extract_ingredients_with_claude(captions, api_key, basics_list)
        except anthropic.AuthenticationError:
            st.error("Invalid Claude API key. Check the Setup section above.")
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
