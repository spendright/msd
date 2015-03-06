# too vague to be useful
BAD_CATEGORIES = {
    'Commercial Products',
    'Industry Innovators',
    'Other',
}

# not useful
BAD_SUFFIXES = [
    ' Brands',
    ' Products',
]

# custom corrections to categories (after normalization)
CATEGORY_ALIASES = {
    'Accessories': 'Fashion Accessories',
    'Bananas and Pineapple': 'Bananas and Pineapples',
    'Food and Beverage': 'Food and Beverages',
    'Food and Drink': 'Food and Beverages',
    'Fun and Games': 'Toys and Games',
    'Misc. Food': 'Food',
    'Occ. Safety and Health Consulting': (
        'Occupational Safety and Health Consulting')
}

# Categories that we can't just split on "and"; e.g.
# Home and Office Furniture, Skin and Hair Care
CATEGORY_SPLITS = {
    'IT Software and Services/Web Design': {
        'IT Software',
        'IT Services',
        'Web Design',
    },
    'Renewable Energy Generation and Installation': {
        'Renewable Energy Generation',
        'Renewable Energy Installation',
    },
    'Sport and Outdoor - Clothing and Shoes': {
        'Sport Clothing',
        'Sport Shoes',
        'Outdoor Clothing',
        'Outdoor Shoes',
    },
    'Home and Office Furniture': {
        'Home Furniture',
        'Office Furniture',
    },
    'Education and Training Services': {
        'Education Services',
        'Training Services',
    },
    'Sports Equipment, Toys and Accessories': {
        'Sports Equipment',
        'Toys',
        'Sports Accessories',
    },
    'Skin and Hair Care': {
        'Skin Care',
        'Hair Care',
    },
    'Sport and Outdoor Clothing': {
        'Sport Clothing',
        'Outdoor Clothing',
    },
    'Surf, Beach and Swimwear': {
        'Surf Wear',
        'Beachwear',
        'Swimwear',
    },
    'Film and Music Production': {
        'Film Production',
        'Music Production',
    },
    'Baby and Children Clothing': {
        'Baby Clothing',
        'Children Clothing',
    },
    'Catering and Meeting/Event Management': {
        'Catering',
        'Meeting Management',
        'Event Management',
    },
    'Waste Reduction Consulting and Services': {
        'Waste Reduction Consulting',
        'Waste Reduction Services',
    },
    'Automotive Sales and Repair': {
        'Automotive Sales',
        'Automotive Repair',
    },
    'Web Design and Development': {
        'Web Design',
        'Web Development',
    },
}
