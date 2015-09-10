Merge Scraper Data (for great justice!)
=======================================

There are a lot of consumer campaigns out there on the Internet. Consumer
campaigns supported by perfectly lovely organizations, organized around
causes you wholeheartedly support, that would change the world if enough
people followed through on them.

But it's hard to put them into practice. And it's *really* hard to put more
than one campaign at a time into practice. Different campaigns have different
scoring systems, different names for the same company, and, when they have
them at all, different apps that don't talk to each other.

``msd`` takes messy data from a bunch of different consumer campaigns, and
puts it into a single unified format.

``msd`` currently powers `SpendRight <http://spendright.org/search>`__
(the author) and the `thinkContext <http://thinkcontext.org>`__ browser
extension.

Using the Data
==============

If you're not there already, check out
`msd's morph.io page <https://morph.io/spendright/msd>`__, where you can
view and download data merged from SpendRight's scrapers.

Keep in mind that the original consumer campaigns are generally copyrighted by
the non-profits that created them, and they have all sorts of different
terms/licensing agreements. It's up to you to decide whether to ask
them for permission now, or forgiveness later. (This applies mostly to the
``claim`` and ``rating`` tables; the facts about companies and brands are
almost certainly fair game.)

Usage
=====

``msd db1.sqlite [db2.sqlite ...]``

This produces a file named ``msd.sqlite`` (you can change this with the ``-o``
switch).

If you don't have the library installed (or are doing development), you
can use ``python -m msd.cmd`` in place of ``msd``.


Data Format
===========

``msd`` uses a SQLite data format, both for input and output.

The input and output format are almost identical; differences are noted
in *italics*.

Keys
----

Every campaign in the input data should have a ``campaign_id``
that would work as a Python identifier (for example ``wwf_palm_oil``).

There isn't a ``company_id`` field though; we just use the shortest name
that a company is commonly referred to by. For example, ``msd`` is smart
enough to figure out that The Coca-Cola Company can be referred to as
simply ``Coca-Cola`` (``The Coca-Cola Company`` appears in a field called
``company_full``; see below).

Similarly, there isn't a ``brand_id`` field, ``msd`` just figures out the
proper name for the brand (minus the ™, etc.), and puts it into the ``brand``
field; the "key" for any given brand is ``company`` and ``brand`` together.

There also aren't (product) category keys; we just put the name of the
category (e.g. ``Chocolate``) into the ``category`` field. ``msd`` tries to
give category names consistent capitalization and formatting, but there
isn't a well-defined category tree per see; see the ``subcategory`` table
below for details.

Finally, the initial data sources each get a ``scraper_id``, which is one
or more identifiers, separated by dots (e.g. ``sr.campaign.wwf_palm_oil``).
These serve only to help you track down problems in your input data.

*Every table in the input data may have a* ``scraper_id`` *field. The stem
of whatever input file data came from will be prepended to form the*
``scraper_id`` *in the output. For example, a* ``scraper_id`` *of
``wwf_palm_oil`` *from an input file named* ``sr.campaign.sqlite``
*would become* ``sr.campaign.wwf_palm_oil`` *in the output data.*

Messy Input Data
----------------

``msd`` *can accept very messy input data. The goal is for you to be able to
put the minimal effort possible into writing a scraper.*

*For starters, the input data need not have primary keys, or any keys at
all. The first thing we do is shovel all the input data into a single
"scratch" table anyways.*

*It's totally fine to have two rows that* would *have the same keys in the
output data;* ``msd`` *will merge them for you.*

*It's totally fine for the input data to be missing fields, or have
fields set to* ``NULL`` *that are supposed to have a value. And it's fine
to have extra fields;* ``msd`` *will just ignore them.*

*For every text field,* ``msd`` *does the following things for you:*

- *converts all whitespace (tabs, double spaces, etc.) to a single space*
- *strips leading and trailing whitespace*
- *converts "smart quotes", ligatures, and other silliness to the plain equivalent*
- *normalizes all unicode into
  `NFKD <http://www.unicode.org/reports/tr15/#Norm_Forms>`__
  (this basically means there aren't multiple ways to represent the same
  accented character).*

*In addition, you can be* even lazier *with the* ``brand`` *field.* ``msd``
*automatically finds ™, ®, etc., puts it elsewhere for safekeeping (see
the* ``tm`` *field, below), and ignores anything after it. For example,
if you throw something like* ``INVOKANA™ (canagliflozin) USPI`` *into
the* ``brand`` *field, it'll know that the brand is named* ``INVOKANA``
*and is supposed to have a ™ after it.*

``msd`` *will infer that companies and brands exist. For example, if you
include a rating for a company in the* ``rating`` *table, a corresponsding
entry will be automatically created for you in the* ``company`` *table.*

Table Definitions
-----------------

brand: facts about brands
^^^^^^^^^^^^^^^^^^^^^^^^^

**Primary Key**: ``company``, ``brand``

**brand**: canonical name for the brand (e.g. ``Dove``)

**company**: canonical name for the company (e.g. ``Unilever``)

**facebook_url**: Optional link to official Facebook page for the brand. (If
there's only a page for the company, put that in ``company.facebook_url``).
So consumers can say nice/brutally honest things on their Facebook page.

**is_former**: 0 or 1. If 1, this brand no longer exists (e.g. Sanyo) or was
sold to another company (e.g. LU is no longer owned by Groupe Danone). Set
this to 1 in your input data to knock out out-of-date brand information from
out-of-date consumer campaigns.

**is_licensed**: 0 or 1. If 1, this brand actually belongs to another company
(e.g. The Coca Cola Company markets products under the Evian brand).
Generally a good idea to put the responsiblity for a brand on its actual
owner.

**is_prescription**: 0 or 1. If 1, this brand is available by prescription
only (so you probably can't buy it on, like, Amazon.com).

**logo_url**: 0 or 1. Optional link to an image of this brand's logo (need not
be to the brand's website).

**tm**: empty string, ``™``, ``®`` or ``℠``. The thing that companies like to
appear directly after the brand name.

**twitter_handle**: handle on Twitter, including the ``@`` (e.g.
``@Electrolux``. So consumers can congratulate them/call them out on
Twitter.

**url**: optional link to official web site/page for this brand. It's okay
if this is just a sub-page of the company's official website.





Data format
-----------

The scraper outputs several SQLite tables.

``campaign`` contains basic information about the campaign, such as its
name, its author, and its URL. Each campaign has an ID (e.g.
``'hope4congo'``), which appears in the ``campaign_id`` field.

``company`` contains facts about a company, such as its full, official
name (``company_full``), URL, and so on and so on.

There *isn't* a ``company_id`` field; rather, this scraper finds a
recognizable, short name, for each company (e.g. "Coca-Cola", "HP")
which appears in the ``company`` field, and that works as a key.
``company`` is also suitable to be displayed to users.

Just like with companies, ``brand`` contains facts about a company. The
``brand`` field should contain the official spelling of a brand, minus
the ™ or ® symbol. ``company`` and ``brand`` together make the unique
key for a brand.

The ``category`` table has one row for each category that each
company/brand is in (``brand`` is set to ``''`` for companies).

``rating`` contains the meat of the campaign data: should I buy from
this brand/company? The keys for these tables are ``campaign_id``,
``company``, and ``brand`` (``''`` for companies), plus a free-text
field, ``scope``, to handle things like a rating applying to a company's
fair trand products.

The various ``scraper_*_map`` tables are mostly for debugging; they tell
the name that the original source used for a company, brand, or
category, and map it to the normalized version we've chosen.

General fields
--------------


Here are some of the fields used in these tables:

-  brand: The name of a brand.
-  campaign: The name of a campaign (not "name" for consistency with
   "brand" and "category"). Only used in the ``campaign`` table;
   everywhere else, ``campaign_id`` is better.
-  campaign\_id: The module name of the scraper this information came
   from. In every table.
-  category: A free-form category description (e.g. "Chocolate")
-  company: The name of a company.
-  date: The date a rating was published. This is in ISO format
   (YYYY-MM-DD), though in some cases we omit the day or even the month.
   A string, not a number!
-  goal: VERY compact description of campaign's goal. Five words max.
-  scope: Used to limit a rating to a particular subset of products
   (e.g. "Fair Trade"). You can have multiple ratings of the same
   brand/company with different scopes.
-  url: The canonical URL for a campaign, company, etc. Other ``*_url``
   fields are pretty common, for example ``donate_url``.

The scrapers whose data we use are allowed to add other fields as needed
(e.g. ``twitter_handle``, ``feedback_url``), so this list isn't
comprehensive.

Rating fields
-------------

Some fields used specifically for ``rating``:

-  score: a numerical score, where higher is better. Used with
   min\_score and max\_score.
-  grade: a US-style letter grade (e.g. A-, C+). Also works for A-E
   rating systems such as used on
   `rankabrand <http://rankabrand.org/>`__ and
   `CDP <https://www.cdp.net/>`__
-  rank: a ranking, where 1 is best. Used with num\_ranked.
-  description: a free-text description that works as a rating (e.g.
   "Cannot recommend")
-  caveat: free-text useful information that is tangential to the main
   purpose of the campaign (e.g. "high in mercury" for a campaign about
   saving fisheries).

This is all very descriptive, but not terribly useful if you want to,
say, compare how a brand fares in several consumer campaigns at once.
That's what the ``judgment`` field is for:

-  judgment: 1 for "support", -1 for "avoid" and 0 for something in
   between ("consider")

Flag fields
-----------

The main use case for this is to match consumer products, so it's
helpful to know if a brand applies to a service, prescription only, or
only marketed to other businesses. We use flags like ``is_prescription``
to call out edge cases like this. For example:

-  \`is\_licensed': set to 1 if licensed from another company
-  ``is_service``: set to 1 if a service, not a product (e.g. Airlines)
-  ``is_prescription``: set to 1 if prescription-only
-  ``is_b2b``: set to 1 if primarly marketed to other businesses (e.g.
   pesticide)

Using the Data
--------------

This is an Open Source project, so *we* don't place any restrictions on
the data. The factual data (``company``, and ``brand``, etc.) probably
isn't really copyrightable anyway.

However, the *campaigns* are copyrighted by the non-profits who created
them, so ideally, you should get their permission before using it for
anything more than research, journalism, etc.

See the
`README <https://github.com/spendright-scrapers/campaigns/blob/master/README.md>`__
for the campaigns scraper for the rules for using each campaign's data.

If all else fails, go with common sense. Most of these organizations are
more interested in changing the world that exercising their intellectual
property rights. Be polite:

-  Give the organization credit and link back to them.
-  Preserve the integrity of the original data; don't censor it or
   interject your own opinions.
-  Don't use it to frustrate the organization's intent (e.g. using the
   HRC Buyer's Guide to support companies that discriminate against LGBT
   employees).
-  Don't pretend you have the organization's endorsement, or that they
   have endorsed specific products (even if they've rated them highly).
-  Link to the organization's donation page. Quality data like this
   takes a lot of time and money to create!
