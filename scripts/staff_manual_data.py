"""Content of the Beamers Farms staff wiki.

Edit the text here, then run:  python scripts/build_staff_manual.py
That regenerates templates/staff_manual_content.html (the searchable wiki page) and the two
downloadable files static/staff-manual.md (Owner) and static/staff-manual-salesperson.md.

Inline markup in any string:  **bold**   `code`
Block types:  ("p", text)  ("steps", heading|None, [..])  ("ul", heading|None, [..])
              ("note", "tip"|"warn"|"info", text)  ("table", [headers], [[row], ...])
audience: "all" = Owner and Salespeople, "owner" = Owner only.
"""

SECTIONS = []


def section(sid, title, audience, summary, *blocks):
    SECTIONS.append({"id": sid, "title": title, "audience": audience, "summary": summary, "blocks": list(blocks)})


# ---------------------------------------------------------------------------------------------
section("how-to-use", "How to use this wiki", "all",
        "Who this is for, what the roles can do, and how to find an answer quickly.",
        ("p", "This wiki is the operating manual for running the Beamers Farms site day to day. It is written as short, numbered procedures so you can follow them while the customer is waiting. Use the **search box** at the top to filter by any word (try `payment`, `cancel`, `coupon`, `report`) or jump straight to a topic from **Contents**."),
        ("table", ["Role", "How you sign in", "What you do"], [
            ["Owner", "Sign-in page → Role **Owner** → the owner password", "Everything: orders, catalogue, prices, stock, coupons, staff accounts, reports, customer messages, community, settings."],
            ["Salesperson", "Sign-in page → Role **Salesperson** → your own username and password", "Handle orders and customers. Which screens you see is set by the Owner for your account (see *Permissions*)."],
            ["Dispatch rider", "Sign-in page → Role **Dispatch rider** → the rider password", "See batched delivery orders and mark an order delivered once the customer has received it."],
        ]),
        ("note", "info", "If a page shows **403 / not allowed**, your account does not have that permission. Nothing is broken: ask the Owner to switch the permission on, or hand the task to someone who has it."),
        ("p", "Sections marked **Owner only** are hidden from salesperson accounts. Procedures show the exact button or menu names you will see on screen, in **bold**."),
        )

# ---------------------------------------------------------------------------------------------
section("run-the-site", "Running the site: the daily routine", "all",
        "A simple opening, during-the-day and closing routine that keeps orders, stock and money consistent.",
        ("steps", "Opening checklist (first 10 minutes)", [
            "Sign in with **your own named account**. Never share a login, and sign out on shared devices.",
            "Open the **Order desk** (Owner: *Owner desk / overview*; Salesperson: *Order operations*). Read the shop status card: **Shop is open** means customers can place orders.",
            "Turn on **alerts on this device** (*Enable owner alerts* / *Enable alerts on this device*) and allow notifications when the browser asks. You are then pinged the moment a new order arrives.",
            "Open the **Live order stream**. Sort by *Oldest first* once to find anything left over from yesterday: orders still **Received**, **Confirmed** or **Preparing**.",
            "Check which orders are **Awaiting payment verification**. Match each one against the business bank account or POS and verify those that have arrived (see *Payments and verification*).",
            "Owner only: look at **Inventory summary** for low-stock items, and at the **abandoned carts** note on the dashboard.",
        ]),
        ("steps", "During the day: the order loop", [
            "A new order alert arrives → open the order from the stream.",
            "Check the items, the delivery zone or pickup choice, the customer's contact details and any processing methods ticked on an item.",
            "Verify the payment in the bank/POS, then press **Verify payment, confirm order**.",
            "Move the order along: **Preparing** → **Out for delivery** (delivery) or **Ready for pickup** (pickup) → **Delivered** or **Picked up**.",
            "Reply to complaints and customer questions as they appear (see *Complaints and customer care*).",
        ]),
        ("steps", "Closing checklist", [
            "Clear the stream: every order today should be **Delivered**, **Picked up**, **Cancelled**, or have a clear next step written in a note for the next shift.",
            "Record any farm-counter sales you have not yet entered (*Record in-person sale*) so stock and reports are correct.",
            "Make sure every cancellation has a reason selected.",
            "Owner only: if you will not take orders overnight, switch the shop to **closed** from the shop status card and say when you reopen.",
            "Sign out.",
        ]),
        ("ul", "Weekly and monthly (Owner)", [
            "Weekly: generate the **Sales report** (*Last 7 days*) and the **Inventory summary**; compare cancellations in the **Order summary**; restock and update stock counts.",
            "Weekly: review open complaints, reviews awaiting a response, and community reports.",
            "Monthly: generate the **Sales report** for *This month*, check coupon usage, review staff permissions and the **Staff report**, deactivate accounts that are no longer needed.",
        ]),
        ("note", "tip", "The habit that prevents most problems: **verify money first, then change the status, then write down anything unusual.**"),
        )

# ---------------------------------------------------------------------------------------------
section("sign-in", "Signing in, roles and permissions", "all",
        "How to sign in, what each permission unlocks, and what to do when something is blocked.",
        ("steps", "Signing in", [
            "Open the staff sign-in page (`/admin/login`).",
            "Choose your **Role**. Salespeople enter their **username** and password; the Owner and the rider enter the shared role password.",
            "If sign-in fails, check the Role first (a salesperson using the *Owner* role will always fail), then the username. Ask the Owner to **reset your password** if you cannot get in.",
            "Use **Sign out** (top right of your desk) when you finish, especially on shared devices.",
        ]),
        ("table", ["Permission", "What it lets a salesperson do"], [
            ["View the live order stream", "Open **Live order stream** and see incoming website orders."],
            ["View customer contact and delivery details", "See customer names, phone numbers and addresses. Without it you see only order contents."],
            ["Verify incoming POS / bank transfers", "Press **Verify payment, confirm order** after the money is in the account."],
            ["Change order status", "Move orders through the full status list and cancel with a reason."],
            ["Record weigh-ins on legacy orders", "Use **Record actual weights** on older weight-priced orders."],
            ["Open and print customer receipts", "Open and print a customer receipt."],
            ["View final customer balances/refunds on legacy settlement receipts", "See the balance or refund amounts on a legacy settlement receipt."],
            ["View customer complaints", "Open the complaints queue and read each complaint."],
            ["Manage complaints", "Change a complaint's status and add internal notes."],
            ["Moderate community posts, reports and suggestions", "Open **Community support**: reply as Beamers Farms, resolve reports, hide posts."],
            ["Record cash/POS orders at the farm counter", "Use **Record in-person sale**."],
            ["View product stock summary", "Open the **Inventory** page."],
            ["Generate sales reports / inventory summaries / order summaries", "Create each report type for a chosen timeline."],
            ["Receive new-order push alerts while the shop is open", "Get a notification on your device for each new order."],
        ]),
        ("note", "info", "Your **Actions** menu only lists what the Owner has allowed for your account. If a shortcut you expect is missing, the permission is off."),
        ("note", "warn", "Deactivating an account blocks that person on their **next request**. Do this the same day someone leaves or changes role."),
        )

# ---------------------------------------------------------------------------------------------
section("order-lifecycle", "The order lifecycle", "all",
        "The eight statuses, what each one means, and the rules that connect them.",
        ("table", ["Status", "Meaning", "Applies to"], [
            ["Received", "Order placed. Payment is not yet verified. Nothing is promised to the customer yet.", "All orders"],
            ["Confirmed", "Payment verified in the bank/POS and the order accepted.", "All orders"],
            ["Preparing", "The farm is picking, cleaning, processing and packing.", "All orders"],
            ["Out for delivery", "Handed to a rider / dispatched to the delivery address.", "Delivery orders only"],
            ["Ready for pickup", "Packed and waiting at the farm for the customer.", "Pickup orders only"],
            ["Delivered", "The customer has received the order.", "Delivery orders only"],
            ["Picked up", "The customer has collected the order at the farm.", "Pickup orders only"],
            ["Cancelled", "Stopped. Stock is returned to inventory. A reason must be chosen.", "All orders"],
        ]),
        ("ul", "Rules the system enforces", [
            "**No confirmation without verified payment.** Confirmed, Preparing, Out for delivery, Ready for pickup, Delivered and Picked up all require the payment to be verified first.",
            "**Verify payment while the order is Received** (or when you press **Verify payment, confirm order**, which verifies and confirms together). Payment can't be verified once fulfilment has begun.",
            "**Pickup and delivery are separate paths.** A pickup order goes Preparing → Ready for pickup → Picked up. A delivery order goes Preparing → Out for delivery → Delivered.",
            "**Cancelling returns the stock** of every item. Reopening a cancelled order takes the stock out again and is refused if there isn't enough.",
        ]),
        ("note", "tip", "Customers can follow their order on the **Track order** page using their order reference, and may get push notifications when an order is confirmed or out for delivery. Keeping statuses accurate is how you keep customers informed."),
        )

# ---------------------------------------------------------------------------------------------
section("handle-order", "Handling an order, step by step", "all",
        "The full procedure from the new-order alert to a completed order, for delivery and for pickup.",
        ("steps", "Step by step", [
            "**Open the order.** Tap the new-order alert, or open the order from the **Live order stream** or the dashboard list. Each order has a reference like `#A1B2C3`.",
            "**Read the order.** Check every line: product, quantity, and any **Processing** methods the customer ticked (for example *Cut into pieces, Vacuum sealed*). Check whether it is **delivery** (and which zone) or **farm pickup**.",
            "**Check the money.** Look in the business bank account or POS for the exact amount due now (see *Payments and verification*). Do not rely on a screenshot.",
            "**Verify and confirm.** Optionally type the **POS / bank reference**, then press **Verify payment, confirm order**. The status becomes *Confirmed* and the customer is notified where push or WhatsApp updates are enabled.",
            "**Prepare.** Set the status to **Preparing** when picking and packing starts.",
            "**Dispatch or hold for pickup.** Delivery: set **Out for delivery** (the rider sees it in their batch). Pickup: set **Ready for pickup**.",
            "**Close it.** When the customer has the goods, set **Delivered** (delivery) or **Picked up** (pickup). The rider can also mark a delivery as delivered.",
            "**If anything goes wrong**, do not delete or hide the order. Add a note, or cancel with the correct reason (see *Cancellations and stock*).",
        ]),
        ("table", ["", "Delivery order", "Pickup order"], [
            ["Fee", "Fee of the chosen delivery zone is added at checkout", "Free"],
            ["Path", "Received → Confirmed → Preparing → Out for delivery → Delivered", "Received → Confirmed → Preparing → Ready for pickup → Picked up"],
            ["Customer needs", "A reachable phone and a correct address", "To collect at the farm during opening hours"],
            ["Typical delay cause", "Wrong address, rider capacity", "Customer not collecting"],
        ]),
        ("note", "warn", "Only change a status when the real-world step has happened. Marking **Delivered** early tells the customer something untrue and hides a real problem."),
        )

# ---------------------------------------------------------------------------------------------
section("payments", "Payments and verification", "all",
        "How customers pay, and the one rule that protects the farm's money.",
        ("p", "Customers choose how to pay at checkout. **Bank transfer** (manual transfer to the business account) is always available. **OPay checkout** appears only when the Owner has enabled the OPay integration. Either way, an order is created as **Received** with payment **not yet verified**."),
        ("steps", "Verifying a bank or POS payment", [
            "Open the order and note the **exact amount due now**.",
            "Open the business bank app or POS statement and find a **completed credit** for that exact amount, ideally with the customer's name or order reference.",
            "Back on the order, enter the **POS / bank reference** if you have it (optional but helpful).",
            "Press **Verify payment, confirm order**. The payment status changes to *Payment verified* and the order becomes *Confirmed*.",
        ]),
        ("ul", "Never do this", [
            "Never confirm because a customer sent a **screenshot** or says they paid. Screenshots can be edited.",
            "Never confirm a *pending* or *reversed* credit. Wait until it is completed.",
            "Never confirm when the amount is **less** than the amount due. Ask the customer for the balance, or cancel with *Payment not received*.",
            "Never mark an order paid from the customer's browser return page alone. The system only trusts a verified credit (or a server-verified OPay callback).",
        ]),
        ("note", "info", "Amounts are in Naira (₦). A customer who overpays should be flagged to the Owner so the extra can be refunded or credited and recorded."),
        )

# ---------------------------------------------------------------------------------------------
section("cancellations", "Cancellations, stock and reopening", "all",
        "When to cancel, which reason to choose, and what cancelling does to stock.",
        ("steps", "Cancelling an order", [
            "Open the order → **Update status**.",
            "Set **Status** to **Cancelled**.",
            "Pick the closest **Reason for cancelling**.",
            "Press **Save status**. Stock is returned to the shelf automatically and the reason is stored.",
        ]),
        ("table", ["Reason", "Use it when"], [
            ["Customer changed their mind", "The customer decided not to buy."],
            ["Customer requested cancellation", "The customer asked you to cancel an order they placed."],
            ["Payment not received", "The money never arrived or was short, and the customer did not fix it."],
            ["Out of stock", "An item can't be supplied."],
            ["Delivery address or zone problem", "The address is outside the zones or can't be found."],
            ["Customer unreachable", "You could not contact the customer after reasonable tries."],
            ["Duplicate order", "The same order was placed twice."],
            ["Other", "Anything else. Add a short factual note."],
        ]),
        ("ul", "Good practice", [
            "The reason shows in the **Order summary** report, so choose the most honest one rather than *Other*.",
            "If a customer already paid, tell the Owner **before** cancelling so the refund is handled and recorded.",
            "To reopen a cancelled order, set a new status. It is refused if stock is no longer sufficient. Restock first.",
        ]),
        )

# ---------------------------------------------------------------------------------------------
section("weights-refunds", "Weights, balances and refunds", "all",
        "Older weight-priced orders, final amounts, and how balances and refunds are recorded.",
        ("p", "Some older orders were priced by weight. For these, the order page shows **Record actual weights**, and the final amount is calculated from the real weight."),
        ("steps", "Recording actual weights (needs the weigh-in permission)", [
            "Weigh each item when packing.",
            "Open the order and find **Record actual weights**.",
            "Enter the weight of each line and press **Save weights and calculate final amount** (salespeople: **Save legacy weigh-in**).",
            "Check the final amount against what the customer paid. A difference becomes a **balance** to collect or a **refund** to pay.",
        ]),
        ("steps", "Balance or refund (Owner order page)", [
            "Open **Balance or refund** on the order.",
            "To collect a balance: enter **Amount received**, **Method**, **Reference / note**, then **Record balance received**.",
            "To pay a refund: enter **Refund amount**, **Method**, **Reference / note**, then **Record refund paid**.",
            "Both are saved under **Payment and adjustment records** on the customer's profile.",
        ]),
        ("note", "warn", "Do not promise a refund, discount or credit that is not in this workflow. Escalate to the Owner."),
        )

# ---------------------------------------------------------------------------------------------
section("order-stream", "Live order stream, batching and riders", "all",
        "Watching incoming orders, searching them, and how deliveries are grouped for riders.",
        ("steps", "Using the live order stream", [
            "Open **Actions → Live order stream** (or the button on your desk).",
            "Use **Search the stream** to find an order by reference (and by customer name or phone if you may view customer details).",
            "Use **Sort by**: *Newest first* for new work, *Oldest first* to catch stragglers, *Highest value* to prioritise big orders.",
            "Open any row to work on the order.",
        ]),
        ("p", "Delivery orders can be grouped into **dispatch batches** so a rider takes several nearby deliveries in one trip. Each batch has a number and a delivery time window (ETA). Riders sign in with the **Dispatch rider** role, see their batches and mark orders **delivered** once handed over."),
        ("steps", "Owner: change how batches are formed", [
            "Open **Live order stream** and find the batching settings.",
            "Set **Batch interval (hours)**: how long orders are collected into one batch (between 0.25 and 24 hours; the default is 2).",
            "Set **Batch delivery weight limit**: the most weight one batch should carry (default 50).",
            "Press **Save batching**. New orders follow the new rules.",
        ]),
        ("note", "tip", "Only orders in **Out for delivery** are shown to the rider for delivery. If a rider says they can't see an order, check its status and that it is a delivery order."),
        )

# ---------------------------------------------------------------------------------------------
section("in-person", "Recording in-person (farm counter) sales", "all",
        "How to record cash or POS sales made at the farm so stock and reports stay correct.",
        ("p", "Needs the **Record cash/POS orders at the farm counter** permission (Owner always has it)."),
        ("steps", "Record a sale", [
            "Open **Actions → Record in-person sale**.",
            "Add the products and quantities sold.",
            "Enter **Buyer name** and **Buyer phone**.",
            "Enter the **Cash/POS reference** (the POS slip number or a note such as *cash*).",
            "Optional: set **Sale date and time** if you are recording a sale made earlier. Leave it empty to use the current time.",
            "Press **Record sale in inventory**. Stock goes down immediately.",
        ]),
        ("ul", "Notes", [
            "In-person sales appear in reports as **farm-counter** sales, separate from website orders.",
            "Record sales the same day. Late entries cause stock counts to drift.",
            "If you record a sale by mistake, tell the Owner. Do not make an opposite sale to cancel it out.",
        ]),
        )

# ---------------------------------------------------------------------------------------------
section("customers", "Customer accounts and privacy", "all",
        "Reading customer information safely and what the account status labels mean.",
        ("ul", "Golden rules", [
            "Customer profiles are **private business records**. Verify who you are speaking to before discussing an order.",
            "Never copy phone numbers, addresses, emails, coupon or note data into personal chats or apps.",
            "Only see what you need. Without the *view customer details* permission you will see order contents but not contact details. That is by design.",
        ]),
        ("table", ["Account status", "Meaning"], [
            ["Verified", "The customer's email address has been confirmed with a code."],
            ["Unverified", "The email is missing or still awaiting confirmation."],
            ["Private Community Profile", "The customer has not opted into public community discovery."],
        ]),
        ("steps", "Owner: finding and reading a customer", [
            "Open **Actions → Manage customer accounts**.",
            "Search by name, phone or email, or filter by **Segment**.",
            "Open a customer. The profile shows contact information, account health, order history, payment and adjustment records, shopping behaviour, current or abandoned cart, recently viewed pages, preferences, engagement, support tickets, messages and notes.",
            "Open the **Attached coupons** dropdown to see every coupon on this customer and whether it is active or paused.",
            "Add a **private note** with only factual, work-related information, then **Save internal note**.",
        ]),
        ("steps", "Owner: account actions", [
            "**Verification reminder**: nudge a customer to confirm their email.",
            "**Reset password**: open the *Reset customer password* dropdown, enter a temporary password (at least 8 characters), press **Reset password**, and give it to the customer privately.",
            "**Restrict community posting**: stops a customer posting in the community; the same button restores it.",
        ]),
        ("note", "warn", "Report any suspected data exposure straight away (see *Security and escalation*). Do not wait until the end of the day."),
        )

# ---------------------------------------------------------------------------------------------
section("complaints", "Complaints and customer care", "all",
        "How to work the complaints queue so every complaint has an owner, a status and a record.",
        ("p", "Complaints arrive from customers through the site. Viewing needs **View customer complaints**; changing them needs **Manage complaints**."),
        ("table", ["Status", "Use it when"], [
            ["New", "Nobody has looked at it yet."],
            ["Under Review", "You are checking the order, contacting the customer or waiting for the Owner."],
            ["Resolved", "The customer has an answer or a fix."],
            ["Closed", "Finished and no further action is needed."],
        ]),
        ("steps", "Handling a complaint", [
            "Open **Actions → Manage complaints** (Owner: *Customer care queue*).",
            "Search by complaint ID, order reference, customer name, phone, subject or status, or filter by status.",
            "Open the complaint and read the customer's message and the **related order**.",
            "Set the status to **Under Review** and write what you checked in **Internal notes**.",
            "Contact the customer through the approved channel, then record what was said or promised.",
            "When done, set **Resolved**, or **Closed** once everything is finished, and press **Save complaint**. The customer receives an account notice that the complaint was updated.",
        ]),
        ("note", "warn", "Do not promise refunds, discounts or delivery times outside the approved workflow. Write what you found and escalate to the Owner."),
        )

# ---------------------------------------------------------------------------------------------
section("community", "Community moderation", "all",
        "Answering customers, handling reports and keeping the community safe. Needs the community permission for salespeople.",
        ("p", "Salespeople see **Community support** only when the Owner has granted **Moderate community posts, reports and suggestions**."),
        ("steps", "Daily community routine", [
            "Open **Actions → Community support**.",
            "Read **No unanswered posts** / unanswered posts and answer with **Reply as Beamers Farms**. Replies from staff appear as official messages.",
            "Open **reports**: read why a post was reported, then **Resolve** the report, or **Hide post** / **Hide reply** if it breaks the rules (abuse, private data, spam, scams).",
            "Read **Ideas and feedback**, and pass useful suggestions to the Owner.",
            "To jump to a specific post, use **Find post by ID** (every post shows `Post #id`).",
        ]),
        ("steps", "Owner: open or close the community", [
            "In **Community support**, use the open/closed switch.",
            "When closed, write the **Closed message** customers will see and press **Save message**.",
        ]),
        ("note", "tip", "Official posts from the farm show as **Admin** and keep the green special-post style."),
        )

# ---------------------------------------------------------------------------------------------
section("reviews", "Reviews", "owner",
        "Moderating customer reviews and responding to them.",
        ("p", "After a customer's first order is at least **Received** and not cancelled, they are invited to leave a short review on the order-success page. One review per order is allowed."),
        ("steps", "Moderate reviews", [
            "Open **Actions → Manage reviews**.",
            "Use **Filter by status** and press **Apply filter**.",
            "For each review choose the **Publication status** (shown or hidden) and write an **Owner response** if useful.",
            "Press **Save moderation**.",
        ]),
        ("note", "tip", "Answer both good and bad reviews politely and factually. A calm reply to a bad review is read by every future customer."),
        )

# ---------------------------------------------------------------------------------------------
section("reports", "Reports: generating, sharing and printing", "all",
        "How to create each report, check it, and print or save it with or without the cover page.",
        ("table", ["Report", "What it shows", "Where"], [
            ["Sales report", "Headline figures, orders by status, a daily timeline, products sold and sales channels.", "Actions → Sales report"],
            ["Order summary", "Orders in the period with status counts and cancellation reasons.", "Actions → Order summary"],
            ["Inventory summary", "Stock on hand and activity in the period; can filter low stock.", "Actions → Inventory summary"],
            ["Staff report", "Each salesperson's profile, status and optional action history.", "Owner: Staff access → Generate staff report"],
        ]),
        ("steps", "Generate a report", [
            "Open the report from **Actions**.",
            "Choose the **Timeline** / **Order timeframe**: *Today, Last 7 days, Last 30 days, This month, This year, All time* or *Custom range* (then set **Start date** and **End date**).",
            "Press **Generate report** / **Apply filters**.",
            "Check the figures on screen. Read **How these figures are calculated** at the bottom of the Sales report if a number surprises you.",
        ]),
        ("steps", "Print or save as PDF", [
            "Press **Print / Save as PDF**.",
            "When asked, choose whether to **include the cover page**. The cover shows the reporting period, who prepared the report and the date. Choose *Cancel* to print without it.",
            "On the staff report you are also asked whether to include the **logged actions**.",
            "In the browser print window, choose **Save as PDF** or your printer, and keep **Background graphics** on so the cover prints in colour.",
        ]),
        ("note", "warn", "Before you print, confirm the period, the status counts and who is allowed to see customer details. Reports are internal documents."),
        ("note", "info", "Dates use **Osogbo local time (WAT)**. A sale at 23:50 belongs to that day, not the next."),
        )

# ---------------------------------------------------------------------------------------------
section("inventory", "Inventory and stock", "all",
        "Reading stock, understanding how it moves, and what to do about low stock.",
        ("ul", "How stock moves", [
            "Stock is counted in **physical sale units** (for example birds, crates or kilograms, depending on the product).",
            "It **decreases** when an order is placed and when an in-person sale is recorded.",
            "It **increases** when an order is cancelled.",
            "The Owner changes **Stock on hand** on the product edit page when new stock arrives or a count shows a difference.",
        ]),
        ("steps", "Check stock (needs the inventory permission)", [
            "Open **Actions → Inventory** (salespeople) or **Inventory summary** (Owner).",
            "Choose the order timeframe and press **Apply filters**.",
            "Use **Search product** to find one item, and the low-stock filter to list items near their alert level.",
        ]),
        ("note", "warn", "If the screen and the shelf disagree, **do not edit orders to make the numbers match**. Tell the Owner. The count and the cause must both be recorded."),
        )

# ---------------------------------------------------------------------------------------------
section("products", "Managing products", "owner",
        "Adding and editing products, prices, stock, minimum quantities and processing methods.",
        ("steps", "Add a product", [
            "Open **Actions → Manage products** and press **New Product** (top right of the page).",
            "Fill in **Product name** and **Description**.",
            "Set **Price per unit (₦)** and the **Price unit** (what the price is per, such as *bird* or *kg*).",
            "Set **Stock on hand**, **Minimum order quantity** and **Low-stock alert at** (the level at which it shows as low).",
            "Add **Optional processing methods** if customers can request them (see below).",
            "Upload a **Product image**, then submit.",
        ]),
        ("steps", "Edit or hide a product", [
            "In **Prices and availability**, open the product (use **Search products** to find it).",
            "Change any field and press **Save changes**.",
            "Use **Should customers see this product?** to show or hide it without deleting it, and **Where should this Beamers product appear?** to choose where it is displayed.",
        ]),
        ("ul", "Processing methods", [
            "Enter each method on its own line or separated by commas, up to eight, for example *Cut into pieces*, *Cleaned and gutted*, *Vacuum sealed*.",
            "Customers can tick **any number** of methods (or none) on the product page and in the cart.",
            "The chosen methods appear on the order, on receipts and on the salesperson's order page, so **prepare the order exactly as listed**.",
        ]),
        ("note", "tip", "Update stock the moment it changes. Customers cannot order more than the stock on hand."),
        )

# ---------------------------------------------------------------------------------------------
section("packages", "Predefined packages", "owner",
        "Bundles of fixed quantities that customers add to the cart in one click.",
        ("steps", "Create a package", [
            "Open **Actions → Predefined packages** and press **New Package** at the top.",
            "Enter **Package name** and a **Short description**.",
            "Set the **Package discount (%)** applied when the whole bundle is bought.",
            "Choose the products and the fixed quantity of each.",
            "Press **Save package**.",
        ]),
        ("ul", "Notes", [
            "Use the toggle on a package to hide or show it without deleting it.",
            "A package can only be sold while its products are in stock. Keep stock current.",
        ]),
        )

# ---------------------------------------------------------------------------------------------
section("coupons", "Coupons and gifting", "owner",
        "Creating coupons, controlling who can use them and gifting them to customers.",
        ("steps", "Create a shared coupon", [
            "Open **Actions → Coupons** and press **New Coupon** at the top.",
            "Enter a **Code** (letters, numbers, `_` or `-`, for example `WELCOME10`).",
            "Choose the **Type** (percent or fixed amount) and the **Value**.",
            "Optional limits: **Minimum spend**, **Maximum uses** and **Excluded product IDs**.",
            "Press **Create coupon**. Use the toggle on the coupon to pause or restart it.",
        ]),
        ("steps", "Gift a coupon", [
            "Under **Gift to selected customers**: choose the **Coupon template** (an active shared coupon), type the **Customer ID(s)**, add a **Gift message**, press **Gift selected customers**.",
            "Under **Gift to all active customers**: choose the template, add a message, press **Gift all customers**.",
            "A coupon is never given twice to the same account. Gifted coupons appear in the customer's profile and in the **Attached coupons** dropdown.",
        ]),
        ("ul", "Why a coupon may not apply at checkout", [
            "It is paused, expired, or has reached its **Maximum uses**.",
            "The cart is below the **Minimum spend**.",
            "A product in the cart is on the **excluded** list.",
            "The coupon belongs to a different customer (gifted coupons only work for the account they were gifted to).",
        ]),
        )

# ---------------------------------------------------------------------------------------------
section("delivery-zones", "Delivery zones and fees", "owner",
        "Setting the areas you deliver to and what each costs.",
        ("steps", "Add a zone", [
            "Open **Actions → Delivery zones** and press **New Delivery zone** at the top.",
            "Enter the **Zone name**, the **Included areas / customer guidance** (what customers read) and the **Delivery fee (₦)**.",
            "Press **Add delivery zone**.",
        ]),
        ("ul", "Notes", [
            "Edit a zone any time with **Save changes**. Use the toggle to archive a zone customers should no longer see.",
            "Farm pickup is offered as a free option in the checkout list. Keep it active unless you stop taking pickups.",
            "If many orders are cancelled for *Delivery address or zone problem*, your zone wording needs improving.",
        ]),
        )

# ---------------------------------------------------------------------------------------------
section("content", "Updates, gallery, partner listings and other site content", "owner",
        "Keeping the public pages fresh: updates, photos, supplier offers, recommendations and trust rules.",
        ("steps", "Post an update", [
            "Open **Actions → Post an update** and press **New Update** at the top.",
            "Enter the **Topic** and **Message**, add an optional **Image**, and check **Posted by**.",
            "Submit. The update appears on the public **Updates** page. Use **Delete** under *Previous updates* to remove one.",
            "Tip: write a page path such as `/products` in your text and it becomes a working link to that page.",
        ]),
        ("steps", "Add to the gallery", [
            "Open **Actions → Manage gallery** and press **New Gallery item**.",
            "Add a **Title**, **Caption / description** and the **Photo** (browser-friendly photos or video).",
            "Set **Display order** (lower numbers show first) and submit. Use the toggle or **Delete** to hide or remove items.",
        ]),
        ("steps", "Partner (supplier) listings", [
            "Open **Actions → Partner advertisements** and press **New Partner listing**.",
            "Enter the **Offer / product name**, **Category**, **Supplier / business name**, **Description**, **Price (₦)** and **Price note**, an optional image, and the supplier's contact details and links.",
            "Set **Display order** and submit.",
            "To let a supplier submit their own offer, create a verified invite. Each invite expires after 24 hours and accepts one submission.",
        ]),
        ("p", "Partner listings are independent businesses, not Beamers Farms products. Keep them clearly separate from your own products."),
        ("steps", "Order-success recommendations", [
            "Open **Actions → Order-success recommendations**.",
            "Tick the **products** and **partner listings** you want shown on the order-success page as *You may also like*.",
            "Press **Save “You may also like”**.",
        ]),
        ("steps", "Privacy rules", [
            "Open **Actions → Privacy & rules** and press **New Privacy rule**.",
            "Enter the **Rule title**, **Rule text** and **Display order**, then press **Add rule**.",
            "Rules appear on the public **Privacy & security** page. Use the toggle to hide a rule.",
        ]),
        )

# ---------------------------------------------------------------------------------------------
section("messaging", "Messaging customers", "owner",
        "Sending a message by push, WhatsApp or email, and reading the delivery results.",
        ("steps", "Send a message", [
            "Open **Actions → Message customers** and press **New Customer message** at the top.",
            "Check **Delivery readiness**: a channel must say **Ready** to be used.",
            "Write the **title** and **message**, choose one or more channels, and attach a file or image if you are using email.",
            "Confirm and send. The message is sent immediately.",
        ]),
        ("table", ["Channel", "A customer is reached only if"], [
            ["Push", "They enabled push notifications and have an active browser subscription."],
            ["WhatsApp", "They agreed to WhatsApp updates and have a valid phone number. Only an approved campaign template is used."],
            ["Email", "They have a verified email address. Attachments go by email only."],
        ]),
        ("table", ["Result", "Meaning"], [
            ["Delivered", "The provider accepted the message for that customer and channel."],
            ["Skipped", "The customer could not be reached on that channel (no consent, no valid contact or no subscription). This is normal, not an error."],
            ["Failed", "We tried and the provider refused or errored. Open **Recent delivery issues** under the campaign to see why."],
        ]),
        ("note", "warn", "Only message customers about their orders, the farm's products or genuine offers. Never send private data in a broadcast."),
        )

# ---------------------------------------------------------------------------------------------
section("staff-accounts", "Staff accounts, permissions and profiles", "owner",
        "Creating accounts, choosing what each person can do, and keeping staff records complete.",
        ("steps", "Create a salesperson account", [
            "Open **Actions → Manage staff** and press **New Staff account** (top right of the page).",
            "Enter the person's name and a unique **username**, and set a strong password.",
            "Give them their credentials **privately**, and ask them to complete their profile.",
        ]),
        ("steps", "Choose what they can do", [
            "Find the account (use **Search staff** by ID, name or username).",
            "Open **Manage operations and alerts**.",
            "Tick only the permissions the person needs, grouped as *Order desk*, *Customer care*, *Counter and stock*, *Reports* and *Alerts*.",
            "Press **Save permissions**. The change applies on their next page load and their **Actions** menu updates.",
        ]),
        ("steps", "Staff profile and staff report", [
            "Each account has a **Staff profile** dropdown: phone, email, socials and address. Staff can fill one field now and the rest later.",
            "Open **Generate staff report** for a printable summary of every salesperson: profile completeness, status, dates and an optional action history.",
        ]),
        ("steps", "Reset, deactivate, reactivate", [
            "**Reset password**: use the account's reset form and share the new password privately.",
            "**Deactivate** when someone leaves. They are blocked on their next request. Their history stays in the records.",
            "Reactivate only if you are certain the person should have access again.",
        ]),
        ("note", "tip", "Start with the default permissions and add more only when needed (**least access**). Review the list monthly."),
        ("p", "**For salespeople:** open **Actions → Staff profile** to update your own phone, email, social links or address. Keep them current so the Owner can reach you."),
        )

# ---------------------------------------------------------------------------------------------
section("vault", "Secure asset vault", "all",
        "Sharing a private file, text or one-time link safely instead of using chat apps.",
        ("steps", "Store something in the vault", [
            "Open **Actions → Secure drop** and press **New drop** at the top.",
            "Choose **What are you dropping?** and add the **Text to share** or a **File or image**.",
            "Optionally set a **password**, or choose a **One-time link**.",
            "Press **Store in vault**. Copy the text or the link with **Copy text** / **Copy link**, then press **Done**.",
        ]),
        ("note", "warn", "Send passwords through a different channel from the link. Remove vault items you no longer need."),
        )

# ---------------------------------------------------------------------------------------------
section("alerts", "Alerts and notifications", "all",
        "Getting new-order alerts on your phone or computer, and fixing alerts that don't arrive.",
        ("steps", "Turn alerts on", [
            "On your desk, press **Enable alerts on this device** (Owner: **Enable owner alerts on this device**).",
            "Allow notifications when the browser asks.",
            "Do this on each device you use. **Disable alerts here** turns them off on that device.",
        ]),
        ("ul", "If alerts don't arrive", [
            "Check the browser still has notification permission for the site.",
            "Check you are not in a silent or battery-saver mode that blocks notifications.",
            "Salespeople: confirm **Receive new-order push alerts** is switched on for your account.",
            "Alerts are sent for new orders while the shop is open. When the shop is closed, check the stream manually.",
            "The alert is a prompt only. The **Live order stream** is always the source of truth.",
        ]),
        )

# ---------------------------------------------------------------------------------------------
section("shop-settings", "Shop open/closed, analytics and other owner tools", "owner",
        "The controls that affect the whole site.",
        ("steps", "Open or close the shop", [
            "On the Owner desk, use the **shop status card**.",
            "Press the button to switch between **Shop is open** and **Shop is closed**.",
            "While closed, customers cannot place new orders. Open orders you already have continue as normal.",
        ]),
        ("ul", "Other tools", [
            "**Abandoned carts**: the dashboard shows carts left waiting. Recovery reminders go only to signed-in customers who enabled notifications.",
            "**Wholesale requests**: open **Actions → Wholesale requests**, update the **Status**, add **Owner notes** and **Save wholesale request**.",
            "**Active customer forms**: lists the forms customers can currently fill in.",
            "**Site analytics**: choose the **Window**, review **Traffic by page**, and add **Additional public paths** to track. **Clear site analytics** removes the counts.",
        ]),
        ("note", "warn", "**Clear selected data** (Danger zone on the Owner desk) permanently removes the data you tick, such as orders and their payment and refund history. Products, stock, delivery zones, staff accounts and shop settings are never included. You must type **CLEAR** to confirm. Generate and save your reports first. This cannot be undone."),
        )

# ---------------------------------------------------------------------------------------------
section("troubleshooting", "Troubleshooting: when something looks wrong", "all",
        "The most common problems and the quickest safe fix.",
        ("table", ["Problem", "Likely cause", "What to do"], [
            ["I can't confirm an order", "Payment isn't verified yet.", "Check the bank/POS, then use **Verify payment, confirm order**."],
            ["A page says 403 / not allowed", "Your account lacks that permission.", "Ask the Owner to enable it, or hand the task over."],
            ["I can't see a customer's phone or address", "Customer details permission is off.", "Ask the Owner. Do not ask a customer to repeat details in public."],
            ["A status option is missing or refused", "Pickup and delivery use different statuses.", "Use **Ready for pickup / Picked up** for pickup and **Out for delivery / Delivered** for delivery."],
            ["Can't reopen a cancelled order", "Not enough stock.", "Restock first, then reopen."],
            ["A customer says a coupon won't work", "Expired, paused, used up, minimum spend or exclusion.", "See *Why a coupon may not apply*. Offer an alternative only if the Owner agrees."],
            ["The report is empty", "Wrong timeline or search term.", "Check the **Timeline / Order timeframe**, dates and filters, then **Generate report** again."],
            ["Stock looks wrong", "Late in-person sale or an unrecorded delivery.", "Record missing sales, then tell the Owner about any remaining gap."],
            ["No new-order alert", "Notifications blocked or shop closed.", "See *Alerts and notifications*. Check the stream manually."],
            ["A message campaign shows many Skipped", "Customers have no consent, contact or subscription.", "Normal. Skipped is not an error. Failed is: open **Recent delivery issues**."],
            ["I can't sign in", "Wrong role or username.", "Choose the right **Role**; ask the Owner to reset your password."],
        ]),
        ("note", "info", "If the same problem repeats, write down the time, the page and what you pressed, and send it to the Owner. That detail makes a fix possible."),
        )

# ---------------------------------------------------------------------------------------------
section("security", "Security and escalation", "all",
        "How to protect the business and who to tell when something is wrong.",
        ("ul", "Everyday security", [
            "Use your **own** account only. Never share passwords or let someone work under your login.",
            "Sign out on shared or public devices.",
            "Never write customer data or passwords into personal chats, notes or screenshots.",
            "Never delete a record to hide a mistake. Use the correction workflow (cancel with a reason, add a note) so there is a true history.",
            "Be suspicious of urgent requests to change an account, bypass verification or send money.",
        ]),
        ("table", ["Escalate to the Owner immediately", "Examples"], [
            ["Money", "Payment mismatch, overpayment, a customer demanding a refund or discount, a missing credit."],
            ["Privacy / security", "Suspected account compromise, a customer's data seen by the wrong person, lost phone with the desk signed in."],
            ["Stock", "A discrepancy between the system and the shelf, spoiled or contaminated stock."],
            ["Delivery", "A rider incident, a missed promise, a repeated address problem."],
            ["Behaviour", "Abusive or threatening customer contact."],
        ]),
        ("note", "tip", "When you escalate, include: the order reference or customer ID, what happened, what you already did, and what you need decided."),
        )

# ---------------------------------------------------------------------------------------------
section("glossary", "Glossary", "all",
        "Plain-language meanings of the terms used on the desk.",
        ("table", ["Term", "Meaning"], [
            ["Order reference", "The short code on each order, such as `#A1B2C3`, used by customers and staff."],
            ["Verified payment", "The amount due has been seen as a completed credit in the business bank/POS."],
            ["Amount due now", "What the customer must pay now for the order, including any delivery fee."],
            ["Zone", "A delivery area with its own fee. Farm pickup is the free option."],
            ["Processing method", "An optional preparation request on an item, such as *Cut into pieces*."],
            ["Dispatch batch", "A group of delivery orders taken by a rider in one trip, with a time window."],
            ["Stream", "The live list of incoming website orders."],
            ["Skipped (message)", "A customer could not be reached on a channel. Not an error."],
            ["Special / Admin post", "An official community post from the farm, shown with the green style."],
            ["WAT", "West Africa Time, the time zone used in all reports."],
        ]),
        )
