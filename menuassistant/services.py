from django.db.models import Sum
from django.utils.html import strip_tags

from inventory.models import Product, ProductRecipeItem
from orders.models import OrderItem
from announcements.models import SitePage

try:
    from orders.availability import get_product_orderability
except Exception:
    get_product_orderability = None


STOP_WORDS = {
    'ang', 'ano', 'what', 'is', 'are', 'the', 'ng', 'sa', 'ba',
    'may', 'meron', 'mayroon', 'available', 'availability', 'avail',
    'magkano', 'price', 'presyo', 'how', 'much', 'cost',
    'ingredient', 'ingredients', 'recipe', 'sangkap', 'contains',
    'please', 'po', 'paki', 'can', 'you', 'tell', 'me',
    'sino', 'who', 'president', 'philippines', 'school', 'mission',
    'paano', 'gagawa', 'gumawa', 'thesis'
}

SIZE_WORDS = {'regular', 'upgrade', 'mega'}


def normalize_text(text):
    text = (text or '').strip().lower()

    for char in ['?', ',', '.', '!', ':', ';', '-', '_', '/', '\\', '(', ')']:
        text = text.replace(char, ' ')

    return ' '.join(text.split())


def get_words(text):
    return normalize_text(text).split()


def meaningful_words(text):
    return [
        word for word in get_words(text)
        if len(word) >= 3 and word not in STOP_WORDS
    ]


def clean_cms_text(value):
    value = strip_tags(value or '')
    return ' '.join(value.split())


def get_site_page(page_key):
    return SitePage.objects.filter(
        page_key=page_key,
        is_active=True
    ).first()


def product_label(product):
    return product.display_name()


def find_matching_products(question):
    q = normalize_text(question)
    q_words = meaningful_words(q)

    if not q_words:
        return []

    requested_sizes = {
        word.title()
        for word in q_words
        if word in SIZE_WORDS
    }

    products = Product.objects.select_related(
        'product_category',
        'stock'
    ).all().order_by(
        'product_category__name',
        'name',
        'size'
    )

    scored_matches = []

    for product in products:
        product_name = normalize_text(product.name)
        product_display = normalize_text(product.display_name())
        product_category = normalize_text(product.display_category())

        searchable_words = set(get_words(
            f"{product.name} {product.size} {product.category} "
            f"{product.display_category()} {product.product_code or ''} {product.display_name()}"
        ))

        score = 0

        if product_display and product_display in q:
            score += 20

        if product_name and product_name in q:
            score += 12

        product_name_words = set(get_words(product.name))

        if product_name_words and product_name_words.issubset(set(q_words)):
            score += 8

        for word in q_words:
            if word in searchable_words:
                score += 2

            if word in product_category:
                score += 1

        if requested_sizes:
            if product.size in requested_sizes:
                score += 6
            else:
                score -= 5

        if score > 0:
            scored_matches.append((score, product))

    if not scored_matches:
        return []

    scored_matches.sort(key=lambda item: item[0], reverse=True)
    top_score = scored_matches[0][0]

    if top_score >= 10:
        return [
            product for score, product in scored_matches
            if score >= top_score - 2
        ]

    return [
        product for score, product in scored_matches
        if score >= 3
    ]


def get_orderability_text(product):
    if not get_product_orderability:
        return 'Availability checker is not available.'

    result = get_product_orderability(product)

    if result.get('is_orderable'):
        return f"Available. Estimated available servings: {result.get('available_servings', 0)}"

    return f"Unavailable. Reason: {result.get('reason', 'Not available')}"


def build_contact_summary(contact_page):
    if not contact_page:
        return "Contact Us information is not available yet."

    response = "Contact Us Information:\n"

    if contact_page.location:
        response += f"- Location: {contact_page.location}\n"

    if contact_page.contact_number:
        response += f"- Contact Number: {contact_page.contact_number}\n"

    if contact_page.email:
        response += f"- Email: {contact_page.email}\n"

    if contact_page.store_hours:
        response += f"- Store Hours: {contact_page.store_hours}\n"

    if contact_page.content:
        response += f"- Note: {clean_cms_text(contact_page.content)}\n"

    return response.strip()


def answer_site_page_question(q, q_words):
    contact_page = get_site_page('contact_us')
    about_page = get_site_page('about_us')

    if (
        'about us' in q
        or 'about the shop' in q
        or 'about coffee' in q
        or q_words.intersection({'about', 'purpose'})
    ):
        if not about_page:
            return "About Us information is not available yet."

        parts = [
            f"About Us: {about_page.title}",
        ]

        if about_page.subtitle:
            parts.append(clean_cms_text(about_page.subtitle))

        if about_page.content:
            parts.append(clean_cms_text(about_page.content))

        return "\n".join(parts)

    if 'contact us' in q:
        return build_contact_summary(contact_page)

    if q_words.intersection({'contact', 'number', 'phone', 'mobile', 'cellphone', 'cp', 'tawag', 'call'}):
        if contact_page and contact_page.contact_number:
            return f"Contact Number: {contact_page.contact_number}"

        return "Contact number is not available yet."

    if q_words.intersection({'email', 'gmail'}):
        if contact_page and contact_page.email:
            return f"Email Address: {contact_page.email}"

        return "Email address is not available yet."

    if q_words.intersection({'location', 'address', 'saan', 'where', 'located'}):
        if contact_page and contact_page.location:
            return f"Location: {contact_page.location}"

        return "Location information is not available yet."

    if q_words.intersection({'hours', 'oras', 'open', 'opening', 'store'}):
        if contact_page and contact_page.store_hours:
            return f"Store Hours: {contact_page.store_hours}"

        return "Store hours are not available yet."

    return None


def answer_menu_question(question):
    q = normalize_text(question)
    q_words = set(get_words(q))

    if not q:
        return "Please type a question about the menu, price, availability, best sellers, ingredients, or shop information."

    if q_words.intersection({'hello', 'hi', 'help', 'tulong'}):
        return (
            "Hello! You can ask me things like:\n"
            "- What products are available?\n"
            "- Magkano ang Iced Coffee Regular?\n"
            "- Available ba ang Hot Coffee?\n"
            "- What is the best seller?\n"
            "- Ingredients ng Iced Coffee?\n"
            "- Ano contact number?\n"
            "- Saan location?\n"
            "- Ano store hours?\n"
            "- Ano email?\n"
            "- Ano about us?"
        )

    site_page_answer = answer_site_page_question(q, q_words)

    if site_page_answer:
        return site_page_answer

    if (
        any(phrase in q for phrase in ['best seller', 'best selling', 'best-selling'])
        or q_words.intersection({'bestseller', 'mabenta', 'popular', 'top'})
    ):
        rows = OrderItem.objects.filter(
            order__payment_status='Paid'
        ).exclude(
            order__status='Cancelled'
        ).values(
            'product__id',
            'product__name',
            'product__size'
        ).annotate(
            total_sold=Sum('quantity')
        ).order_by('-total_sold')[:5]

        if not rows:
            return "No best-seller data yet because there are no paid sales records."

        response = "Top best-selling products based on paid orders:\n"

        for index, row in enumerate(rows, start=1):
            size = row['product__size']

            if size and size != 'Not Applicable':
                name = f"{row['product__name']} - {size}"
            else:
                name = row['product__name']

            response += f"{index}. {name} — {row['total_sold']} sold\n"

        return response.strip()

    if q_words.intersection({'menu', 'products', 'items', 'drinks'}):
        products = Product.objects.select_related(
            'product_category'
        ).all().order_by(
            'product_category__name',
            'name',
            'size'
        )

        if not products.exists():
            return "No products are currently listed in the menu."

        response = "Here are the products in the menu:\n"

        for product in products[:20]:
            response += f"- {product_label(product)} — ₱{product.price} ({product.display_category()})\n"

        if products.count() > 20:
            response += f"\nShowing 20 of {products.count()} products."

        return response.strip()

    if q_words.intersection({'available', 'availability', 'avail', 'meron', 'mayroon', 'pwede', 'stock', 'orderable'}):
        matches = find_matching_products(q)

        if not matches:
            return "I could not find a matching product. Please include the product name, for example: available ba Iced Coffee Regular?"

        response = "Product availability:\n"

        for product in matches[:10]:
            response += f"- {product_label(product)}: {get_orderability_text(product)}\n"

        return response.strip()

    if q_words.intersection({'price', 'presyo', 'magkano', 'cost'}):
        matches = find_matching_products(q)

        if not matches:
            return "I could not find a matching product. Please include the product name, for example: magkano Iced Coffee Regular?"

        response = "Product prices:\n"

        for product in matches[:10]:
            response += f"- {product_label(product)}: ₱{product.price}\n"

        return response.strip()

    if q_words.intersection({'ingredient', 'ingredients', 'recipe', 'sangkap', 'contains'}):
        matches = find_matching_products(q)

        if not matches:
            return "I could not find a matching product. Please include the product name, for example: ingredients ng Iced Coffee."

        response = "Product recipe/ingredient details:\n"

        for product in matches[:5]:
            recipe_items = ProductRecipeItem.objects.filter(
                product=product,
                is_active=True,
                ingredient__is_active=True
            ).select_related('ingredient')

            response += f"\n{product_label(product)}:\n"

            if not recipe_items.exists():
                response += "- No active recipe configured.\n"
            else:
                for item in recipe_items:
                    response += f"- {item.ingredient.name}: {item.quantity_required} {item.ingredient.unit}\n"

        return response.strip()

    matches = find_matching_products(q)

    if matches:
        response = "I found these matching products:\n"

        for product in matches[:10]:
            response += f"- {product_label(product)} — ₱{product.price} | {get_orderability_text(product)}\n"

        return response.strip()

    return (
        "Sorry, I can only answer menu and shop information questions for now. "
        "You may ask about product list, price, availability, best sellers, ingredients, contact number, location, store hours, email, or about us."
    )
