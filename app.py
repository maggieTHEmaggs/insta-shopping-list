import re
import streamlit as st
import instaloader
import anthropic

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Insta Shopping List", page_icon="🛒", layout="centered")
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
    """Pull the post shortcode out of an Instagram URL."""
    match = re.search(r"/(?:p|reel|tv)/([A-Za-z0-9_-]+)", url)
    if not match:
        raise ValueError(f"Couldn't parse URL: {url}")
    return match.group(1)


def fetch_caption(shortcode: str) -> str:
    """Fetch the caption of a public Instagram post."""
    L = instaloader.Instaloader(quiet=True, download_pictures=False,
                                download_videos=False, download_video_thumbnails=False,
                                save_metadata=False)
    post = instaloader.Post.from_shortcode(L.context, shortcode)
    return post.caption or ""


def looks_like_recipe(caption: str) -> bool:
    """Rough check: does the caption contain ingredient-style content?"""
    keywords = ["cup", "tbsp", "tsp", "gram", "g ", "ml", "oz", "lb",
                "ingredient", "salt", "pepper", "oil", "flour", "butter",
                "egg", "garlic", "onion", "tomato", "chicken", "beef", "sugar"]
    lower = caption.lower()
    return any(kw in lower for kw in keywords)


def extract_ingredients_with_claude(captions: list[str], api_key: str) -> str:
    """Send all captions to Claude and get back a unified shopping list."""
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

generate = st.button("Generate Shopping List", type="primary",
                     disabled=not (api_key and urls_input.strip()))

if generate:
    urls = [u.strip() for u in urls_input.splitlines() if u.strip()]

    # ── Step 1: Fetch captions ─────────────────────────────────────────────────
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
                    captions.append(caption)  # still try it
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

    # ── Step 2: Extract & merge ingredients ────────────────────────────────────
    with st.spinner("Extracting ingredients with Claude…"):
        try:
            shopping_list = extract_ingredients_with_claude(captions, api_key)
        except anthropic.AuthenticationError:
            st.error("Invalid Claude API key. Check it in the sidebar.")
            st.stop()
        except Exception as e:
            st.error(f"Claude API error: {e}")
            st.stop()

    # ── Step 3: Show result ────────────────────────────────────────────────────
    st.divider()
    st.subheader("🛒 Your Shopping List")
    st.markdown(shopping_list)

    st.download_button(
        label="📥 Download as .txt",
        data=shopping_list,
        file_name="shopping_list.txt",
        mime="text/plain",
    )
