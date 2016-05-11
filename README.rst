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
(``msd``'s creator) and the `thinkContext <http://thinkcontext.org>`__ browser
extension.


Using the data
==============

If you're not there already, check out
`msd's morph.io page <https://morph.io/spendright/msd>`__, where you can
view and download data merged from SpendRight's scrapers.

Keep in mind that the original consumer campaigns are generally copyrighted by
the non-profits that created them, and they have all sorts of different
terms/licensing agreements. It's up to you to decide whether to ask
them for permission now, or forgiveness later.

(This mostly applies to the ``claim`` and ``rating`` tables; facts about
companies and brands are almost certainly fair game.)


Installation
============

It's on PyPI: ``pip install msd``


Usage
=====

``msd db1.sqlite [db2.sqlite ...]``

This produces a file named ``msd.sqlite`` (you can change this with the ``-o``
switch).

``msd`` can also take YAML files as input. The YAML files should encode a
map from table name to list of rows (which are maps from column name to value).
For example::

  campaign:
  - author: Greenpeace International
    campaign_id: greenpeace_palm_oil
  rating:
  - campaign_id: greenpeace_palm_oil
    company: Colgate-Palmolive
    judgment: -1
  - campaign_id: greenpeace_palm_oil
    company: Danone
    judgment: 0

If you don't have the library installed (e.g. for development), you
can use ``python -m msd.cmd`` in place of ``msd``.


Data format
===========

``msd`` uses a SQLite data format, both for input and output.

The input and output format are almost identical; differences are noted
in *italics*.

Keys
----

Every campaign in the input data should have a ``campaign_id``
that would work as a Python identifier (for example ``wwf_palm_oil``).

There isn't a ``company_id`` field though; we just use the shortest name
that a company is commonly referred to by.``msd`` is smart
enough to know that, for example, The Coca-Cola Company can be called
``Coca-Cola`` but that we can't refer to The Learning Company as simply
"Learning".

Similarly, there isn't a ``brand_id`` field, ``msd`` just figures out the
proper name for the brand (minus the ™, etc.), and puts it into the ``brand``
field; the "key" for any given brand is ``company`` and ``brand`` together.

There also aren't (product) category keys; we just put the name of the
category (e.g. ``Chocolate``) into the ``category`` field.

Finally, the initial data sources each get a ``scraper_id``, which is one
or more identifiers, separated by dots (e.g. ``sr.campaign.wwf_palm_oil``).
These serve only to help you track down problems in your input data.

*Every table in the input data may have a* ``scraper_id`` *field to help
identify which code gathered that data. The stem
of whatever input file data came from will be prepended to form the*
``scraper_id`` *in the output.*

*For example, a* ``scraper_id`` *of*
``wwf_palm_oil`` *from an input file named* ``sr.campaign.sqlite``
*would become* ``sr.campaign.wwf_palm_oil`` *in the output data.*

Messy input data
----------------

``msd`` *can accept very, very messy input data. The goal is for you to be
able as little effort as possible into writing scrapers.*

no primary keys
^^^^^^^^^^^^^^^

*For starters, the input data need not have primary keys, or any keys at
all. The first thing we do is shovel all the input data into a single
"scratch" table anyways.*

*It's totally fine to have two rows that* would *have the same keys in the
output data;* ``msd`` *will merge them for you.*

missing/extra fields
^^^^^^^^^^^^^^^^^^^^

*It's totally fine for the input data to be missing fields, or have
fields set to* ``NULL`` *that are supposed to have a value (in the worst case,
if you omit a required value,* ``msd`` *will just ignore that row.*

*It's fine to have extra fields;* ``msd`` *will just ignore them.*

different names for companies and brands
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

*It's fine to use different names for the same company
or brand;* ``msd`` *will figure this out and merge them as appropriate.*

general text cleanliness
^^^^^^^^^^^^^^^^^^^^^^^^

*For every text field,* ``msd`` *does the following things for you:*

- *converts all whitespace (tabs, double spaces, etc.) to a single space*
- *strips leading and trailing whitespace*
- *converts "smart quotes", ligatures, and other silliness to the plain
  equivalent*
- *normalizes all unicode into NFKD form (this basically means there aren't
  multiple ways to represent the same accented character).*

brand name cleaning
^^^^^^^^^^^^^^^^^^^

*In addition, you can be* even lazier *with the* ``brand`` *field.* ``msd``
*automatically finds ™, ®, etc., puts it elsewhere for safekeeping (see
the* ``tm`` *field, below), and ignores anything after it.*

*For example, if you throw something like*
``INVOKANA™ (canagliflozin) USPI`` *into the* ``brand`` *field, it'll know
that the brand is named* ``INVOKANA`` *and is supposed to have a ™ after it.*

category name cleaning
^^^^^^^^^^^^^^^^^^^^^^

``msd`` *formats category names in a consistent way. For example,*
``food & beverages`` *in the input data would become* ``Food and Beverages``
*in the output data.*

rating cleanup
^^^^^^^^^^^^^^

``msd`` can do limited cleanup of ratings, including inferring ``judgment``
from ``grade``. See ``rating`` table for details.

inferred rows
^^^^^^^^^^^^^

``msd`` *will infer that companies and brands exist. For example, if you
include a rating for a company in the* ``rating`` *table, a corresponding
entry will be automatically created for you in the* ``company`` *table.*

and that's not all...
^^^^^^^^^^^^^^^^^^^^^

Nope, that's pretty much everything. Here are the table definitions:


Table definitions
-----------------

brand: facts about brands
^^^^^^^^^^^^^^^^^^^^^^^^^

**Primary Key**: ``company``, ``brand``

**brand**: canonical name for the brand (e.g. ``Dove``)

**company**: canonical name for the company (e.g. ``Unilever``)

**facebook_url**: optional link to official Facebook page for the brand. (If
there's only a page for the company, put that in ``company.facebook_url``).
So consumers can say nice/brutally honest things on their Facebook page.

**is_former**: 0 or 1. If 1, this brand no longer exists (e.g. Sanyo) or was
sold to another company (e.g. LU is no longer owned by Groupe Danone). Set
this to 1 in your input data to knock out out-of-date brand information from
out-of-date consumer campaigns.

**is_licensed**: 0 or 1. If 1, this brand actually belongs to another company
(e.g. The Coca-Cola Company markets products under the Evian brand).
Generally a good idea to put the responsiblity for a brand on its actual
owner.

**is_prescription**: 0 or 1. If 1, this brand is available by prescription
only (so you probably can't buy it on, like, Amazon.com).

**logo_url**: 0 or 1. Optional link to an image of this brand's logo (need not
be on the brand's website).

**tm**: empty string, ``™``, ``®`` or ``℠``. The thing that companies like to
appear directly after the brand name.

**twitter_handle**: optional handle for the brand's Twitter account, including
the ``@`` (e.g. ``@BrownCowYogurt``). So consumers can congratulate them/call
them out on Twitter.

**url**: optional link to official web site/page for this brand. It's okay
if this is just a sub-page of the company's official website.


campaign: consumer campaigns
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In practice, introducing consumer campaigns to users is one of the
most important parts of any tool you build; you'll probably want to just use
this table as a starting point, and include some content of your own.

**Primary Key**: ``campaign_id``

**author**: optional free-form name of the organization behind the campaign
(e.g. ``Greenpeace International``).

**author_url**: optional link to author's website

**campaign**: free-form name of the campaign (e.g.
``Guide to Greener Electronics``)

**campaign_id**: unique identifier for this campaign (e.g.
``greenpeace_electronics``.) Up to you to pick something that makes sense
and doesn't collide with other campaign IDs.

**contributors**: optional free-form description of other contributors
to the consumer campaign (e.g.
``International Labor Rights Forum, Baptist World Aid``).

**copyright**: optional copyright notice. Usually starts with ``©`` (e.g.
``© 2006-2014 Climate Counts. All Rights Reserved.``).

**date**: optional date this campaign was created, in ``YYYY-MM-DD``,
``YYYY-MM``, or ``YYYY`` format. A string, not a number. Sometimes the
best available data is a couple years old, and consumers deserve to know!

**donate_url**: optional link to a page where you can donate back to the
campaign/author. Try to include this somewhere in whatever you build; create a
virtuous cycle and help these consumer campaigns become financially
self-sustaining!

**email**: optional contact email for the campaign (e.g.
``feedback@free2work.org``)

**facebook_url**: optional link to official Facebook page for the campaign,
so consumers can get involved in the movement!

**goal**: very brief (40 characters or less) description of what someone
helps accomplish by being involved in this campaign (e.g.
``stop forced labor in Uzbekistan``). Best to start this with a lowercase
letter unless the first word is a proper noun.

**twitter_handle**: optional handle for the campaign's Twitter account, so
that consumers can follow/reference them on Twitter. Including the ``@``
(e.g. ``@WWF``).

**url**: optional link to campaign's web site, so consumers can learn more
and get involved.


category: product categories for companies and brands
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``msd`` doesn't build an organized category tree like, say, online retailers
have; these are more like hints. See the ``subcategory`` table for details.

**Primary Key**: ``company``, ``brand``, ``category``

**brand**: canonical name for the brand. Empty string if we're categorizing
a company

**category**: free-form name for category (e.g. ``Food and Beverages``).

**company**: canonical name for the company

**is_implied**: 0 or 1. If 1, this category was only implied by a subcategory
relationship (see ``subcategory`` table). *Ignored in the input data.*


claim: bullet points to support ratings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Primary Key**: ``campaign_id``, ``company``, ``brand``, ``scope``, ``claim``

(``claim`` is free-form, so this is more like a non-unique key)

**brand**: canonical name for the brand. Empty string if this is a claim
about a company.

**campaign_id**: unique identifier of campaign making this claim (see
``campaign.campaign_id``)

**claim**: free-form claim. Should be small enough to fit in a bullet point,
and be able to stand on its own (spell out obscure acronyms and other context).
Best to start this with a lowercase letter unless the first word is a
proper noun.

**company**: canonical name for the company

**date**: optional date this claim was made, in ``YYYY-MM-DD``,
``YYYY-MM``, or ``YYYY`` format. A string, not a number.

**judgment**: -1, 0, or 1. Does the claim say something good (``1``), mixed
(``0``), or bad (``-1``) about the company or brand? Need not match the
campaign's rating. If a claim is totally neutral (e.g.
``manufactures large appliances``) it doesn't belong in this table at all!

**scope**: optional free-form limitation on which products this applies to
(e.g. ``Fair Trade``). Usually an empty string, to mean no limitation or that
it's only *not* some scope elsewhere in the data (don't set this to
``Non-Certified``).

**url**: optional link to web page/PDF document etc. where this claim was made.
Some people like to see the supporting data!


company: facts about companies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Primary Key**: ``company``

**company**: canonical name for the company (e.g. ``Disney``)

**company_full**: full, official name of the company (e.g.
``The Walt Disney Company``).

**email**: contact/feedback email for the company (e.g.
``consumer.relations@adidas.com``).

**facebook_url**: optional link to official Facebook page for the company.

**feedback_url**: optional link to a page where consumers can submit
feedback to the company (some companies don't like to do this by email).

**hq_company**: optional name of the country where this company is
headquartered (e.g. ``USA``).

**logo_url**: 0 or 1. Optional link to an image of this company's logo (need
not be on the company's website).

**phone**: optional phone number for customer feedback/complaints (a string,
not a number)

**twitter_handle**: optional handle for the company's Twitter account,
including the ``@`` (e.g. ``@Stonyfield``).

**url**: optional link to official web site/page for this company.


company_name: canoncial, full, and alternate names for companies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Primary Key**: ``company``, ``company_name``

**company**: canonical name for the company (e.g. ``Disney``)

**company_name**: a name for the company. can be the canonical
name, the full name (see ``company.company_full``) or something else
(e.g. ``Walt Disney``).

**is_alias**: 0 or 1. If 1, this is a name that somebody used somewhere
but isn't really a recognizable name for the company (e.g. "AEO" for
American Eagle Outfitters or "LGE" for "LG Electronics"). *Set this your
input data to knock out weird company aliases.*

**is_full**: 0 or 1. If 1, this is the full name for the company,
which also appears in ``company.company_full``. (There isn't an
``is_canonical`` field; just check if ``company = company_name``.)


rating: campaigns' judgments of brands and companies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is where the magic happens.

**brand**: canonical name for the brand. Empty string if this is a rating of
a company.

**campaign_id**: unique identifier of campaign this rating comes from (see
``campaign.campaign_id``)

**company**: canonical name for the company

**date**: optional date this rating was last updated, in ``YYYY-MM-DD``,
``YYYY-MM``, or ``YYYY`` format. A string, not a number.

**description**: free-form, brief description of the rating (e.g.
``Soaring``, ``Cannot Recommend``).

**grade**: optional letter grade (e.g. ``A+``, ``C-``, ``F``). Some campaigns
use ``E`` instead of ``F``.

**judgment**: -1, 0, or 1. Should consumers support (``1``), consider
(``0``), or avoid (``-1``) the company or brand? Some campaigns will give
everything a ``1`` (e.g. certifiers) or everything a ``-1`` (e.g. boycott
campaigns).

``msd`` *can infer* ``judgment`` *from* ``grade``, *but otherwise you need
to set it yourself in the input data.*

*Red for avoid, yellow for consider, and green for support is a de-facto
standard among consumer campaigns. If all else fails, contact the campaign's
author and ask.*

**max_score**: if ``score`` is set, the highest score possible on the rating
scale (a number).

**min_score**: if ``score`` is set, the lowest score possible on the rating
scale (a number). *If* ``score`` *is set but* ``min_score`` *is not,* ``msd``
*will assume* ``min_score`` *is zero.*

**num_ranked**: if ``rank`` is set, the number of things ranked (an integer)

**rank**: if campaign ranks companies/brands, where this one ranks
(this is an integer, and the best ranking is `1`, not `0`).

**scope**: optional free-form limitation on which products this applies to
(e.g. ``Fair Trade``). Usually an empty string, to mean no limitation or that
it's only *not* some scope elsewhere in the data (don't set this to
``Non-Certified``).

**score**: optional numerical score (e.g. ``57.5``).

**url**: optional link to web page/PDF document etc. where this rating was
made. Some people like to see the supporting data!


scraper: when data was last gathered
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Primary Key**: ``scraper_id``

**last_scraped**: when this data was last gathered, as a UTC ISO timestamp
(for example, ``2015-08-03T20:55:36.795227Z``).

**scraper_id**: unique identifier for the scraper that gathered this data


scraper_brand_map: names of brands in the input data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is mostly useful for debugging your output data.

``msd`` *ignores this table if it appears in the input data*

**Primary Key**: ``scraper_id``, ``scraper_company``, ``scraper_brand``

**Other Indexes**: (``company``, ``brand``)

**brand**: canonical name for the brand. (This should never be empty;
that's what ``scraper_company_map`` is for.)

**company**: canonical name for the company

**scraper_brand**: name used for the brand in the input data

**scraper_company**: name used for the company in the input data

**scraper_id**: unique identifier for the scraper that used this
brand and company name


scraper_category_map: names of categories in the intput data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is mostly useful for debugging your output data.

``msd`` *ignores this table if it appears in the input data*

**Primary Key**: ``scraper_id``, ``category``, ``scraper_brand``

**Other Indexes**: (``category``)

**category**: canonical name for a category (e.g. ``Food and Beverages``)

**scraper_brand**: name used for the brand in the input data (e.g.
`` food &  beverages``).

**scraper_id**: unique identifier for the scraper that used this
category name


scraper_company_map: names of companies in the input data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is mostly useful for debugging your output data.

``msd`` *ignores this table if it appears in the input data*

**Primary Key**: ``scraper_id``, ``scraper_company``

**Other Indexes**: (``company``)

**company**: canonical name for the company

**scraper_brand**: name used for the brand in the input data

**scraper_id**: unique identifier for the scraper that used this
company name


subcategory: product category relationships
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``msd`` doesn't attempt to build a proper category tree; it's really just
a directed graph of category relationships: if something is in category
A (``subcategory``) it must also be in category B (``category``).

``msd`` *automatically infers implied relationships: if A is a subcategory
of B and B is a subcategory of C, A is a subcategory of C.*

**category**: canonical name for a category

**is_implied**: 0 or 1. If 1, this relationship was inferred by ``msd``.
*Ignored in the input data.*

**subcategory**: canonical name for a subcategory of ``category``


url: hook for scraping URLs in the scraper data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

*This table only exists in the input data, and is only used to fill fields
in the output data that would otherwise be empty.*

This allows us to build generic scrapers that can grab Twitter handles,
Facebook URLs, etc. directly from a company or brand's official page. See
SpendRight's `scrape-urls <https://github.com/spendright/scrape-urls>`__
for an example.

**facebook_url**: optional facebook page for a company/brand

**last_scraped**: when the company/brand's page was scraped, as a UTC
iso timestamp (e.g. ``2015-08-03T20:55:36.795227Z``). *Not currently used.*

**twitter_handle**: optional twitter handle for a company/brand, including
the leading ``@``.

**url**: url this data was scraped from


Writing your own scrapers
=========================

If you want to write something in Python, check out SpendRight's
`scrape-campaigns <https://github.com/spendright/scrape-campaigns>`__
project, and submit a pull request (look in ``scrapers/``) for examples.

If you'd rather write in another language, consider setting up your own
scraper on `morph.io <https://morph.io/>`__, which can also handle scrapers
in Ruby, PHP, Perl, and Node.js. See the
`morph.io Documentation <https://morph.io/documentation>`__ for details.
And let us know, so we can point
`msd's morph.io page <https://morph.io/spendright/msd>`__ at it.


Working on msd
==============

``msd`` is pretty straightforward. Here's a brief overview of how it works:

1. ``msd`` starts in ``msd/cmd.py`` (look for ``msd.cmd.run()``).
2. It first dumps all the input data into a temporary "scratch" DB
   (``msd-scratch.sqlite``) with the correct columns and useful indexes (look
   for ``msd.scratch.build_scratch_db()``).
3. Then it creates the output database (``msd.sqlite``) and fills it table by
   table (look for ``msd.fill_output_db()``).

Also, table definitions live in ``msd/table.py``.


Using msd as a library
======================

``msd`` isn't really a library, but there's some useful stuff in ``msd``
(for example, ``msd/company.py`` knows how to strip all the various versions
of "Inc." off company names).

If you want to call some of this stuff from another project, please let us
know so that we can work out a sane, stable interface for you!
