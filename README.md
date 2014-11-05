Scrapers for Consumer Campaigns
===============================

The goal of this project is to scrape consumer campaign data into a common
format so that any tool (e.g. websites, browser extensions, apps) can help
people be a part of any consumer campaign.

This "scraper" doesn't actually scrape web pages directly; it's job is to
merge and clean up data from the [campaigns](https://morph.io/spendright-scrapers/campaigns) scraper, so that, for example, a company will be referred to the
same way across campaigns. Eventually, we'll also merge in master
company data scraped directly from company websites.

This is a project of [SpendRight](http://spendright.org). You can contact
the author (SpendRight, Inc.) at dave@spendright.org.


Data format
-----------

The scraper outputs several SQLite tables.

`campaign` contains basic information about the campaign, such as its
name, its author, and its URL. Each campaign has an ID (e.g. `'hope4congo'`),
which appears in the `campaign_id` field.

`company` contains facts about a company, such as its full, official name
(`company_full`), URL, and so on and so on. The `company_category` table
has one row for each category (sector) that a company belongs in.

There *isn't* a `company_id` field; rather, this scraper finds a recognizable, short name, for each company (e.g. "Coca-Cola", "HP") which appears in the `company` field, and that works as a key. `company` is also suitable to be displayed to users.

Just like with companies, `brand` contains facts about a company, and there
is also a `brand_category` table. The `brand` field should contain the official
spelling of a brand, minus the ™ or ® symbol. `company` and `brand` together make the unique key for a brand.

`campaign_brand_rating` and `campaign_company_rating` contain the meat of the
campaign: should I buy from this brand/company? The keys for these tables
are `campaign_id`, `company`, and `brand` (for `campaign_brand_rating`), plus
a free-text field, `scope`, to handle things like a rating
applying to a company's fair trand products.

The various `scraper_*_map` tables are mostly for debugging; they tell
the name that the original source used for a company, brand, or category,
and map it to the normalized version we've chosen.

General fields
--------------

Here are some of the fields used in these tables:

 * brand: The name of a brand.
 * campaign: The name of a campaign (not "name" for consistency with "brand" and "category"). Only used in the `campaign` table; everywhere else, `campaign_id` is better.
 * campaign_id: The module name of the scraper this information came from. In every table.
 * category: A free-form category description (e.g. "Chocolate")
 * company: The name of a company.
 * date: The date a rating was published. This is in ISO format (YYYY-MM-DD), though in some cases we omit the day or even the month. A string, not a number!
 * goal: VERY compact description of campaign's goal. Five words max.
 * scope: Used to limit a rating to a particular subset of products (e.g. "Fair Trade"). You can have multiple ratings of the same brand/company with different scopes.
 * url: The canonical URL for a campaign, company, etc. Other `*_url` fields are pretty common, for example `donate_url`.

The scrapers whose data we use are allowed to add other fields as needed
(e.g. `twitter_handle`, `feedback_url`), so this list isn't comprehensive.


Rating fields
-------------

Some fields used specifically for rating (in the `campaign_*_rating` fields):

 * score: a numerical score, where higher is better. Used with min_score and max_score.
 * grade: a US-style letter grade (e.g. A-, C+). Also works for A-E rating systems such as used on [rankabrand](http://rankabrand.org/) and [CDP](https://www.cdp.net/)
 * rank: a ranking, where 1 is best. Used with num_ranked.
 * description: a free-text description that works as a rating (e.g. "Cannot recommend")
 * caveat: free-text useful information that is tangential to the main purpose of the campaign (e.g. "high in mercury" for a campaign about saving fisheries).

This is all very descriptive, but not terribly useful if you want to, say,
compare how a brand fares in several consumer campaigns at once. That's what
the `judgment` field is for:

 * judgment: 1 for "support", -1 for "avoid" and 0 for something in between ("consider")


Flag fields
-----------

The main use case for this is to match consumer products, so it's helpful
to know if a brand applies to a service, prescription only, or only marketed
to other businesses. We use flags like `is_prescription` to call out
edge cases like this. For example:

 * `is_licensed': set to 1 if licensed from another company
 * `is_service`: set to 1 if a service, not a product (e.g. Airlines)
 * `is_prescription`: set to 1 if prescription-only
 * `is_b2b`: set to 1 if primarly marketed to other businesses (e.g. pesticide)




Using the Data
--------------

This is an Open Source project, so *we* don't place any restrictions on the
data. The factual data (`company`, and `brand`, etc.) probably isn't really
copyrightable anyway.

However, the *campaigns* are copyrighted by the non-profits who created
them, so ideally, you should get their permission before using it for anything
more than research, journalism, etc.

See the [README](https://github.com/spendright-scrapers/campaigns/blob/master/README.md) for the campaigns scraper for the rules for using each campaign's data.

If all else fails, go with
common sense. Most of these organizations are more interested in changing
the world that exercising their intellectual property rights. Be polite:

 * Give the organization credit and link back to them.
 * Preserve the integrity of the original data; don't censor it or
   interject your own opinions.
 * Don't use it to frustrate the organization's intent (e.g. using the
   HRC Buyer's Guide to support companies that discriminate against LGBT
   employees).
 * Don't pretend you have the organization's endorsement, or that they
   have endorsed specific products (even if they've rated them highly).
 * Link to the organization's donation page. Quality data like this takes a lot
   of time and money to create!
