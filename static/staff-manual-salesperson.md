# Beamers Farms Staff Digital Wiki

*Operating manual for Salespeople. Built from the same content as the in-site wiki.*

## Contents

- How to use this wiki
- Running the site: the daily routine
- Signing in, roles and permissions
- The order lifecycle
- Handling an order, step by step
- Payments and verification
- Cancellations, stock and reopening
- Weights, balances and refunds
- Live order stream, batching and riders
- Recording in-person (farm counter) sales
- Customer accounts and privacy
- Complaints and customer care
- Community moderation
- Reports: generating, sharing and printing
- Inventory and stock
- Secure asset vault
- Alerts and notifications
- Troubleshooting: when something looks wrong
- Security and escalation
- Glossary

## How to use this wiki

*Who this is for, what the roles can do, and how to find an answer quickly.*

This wiki is the operating manual for running the Beamers Farms site day to day. It is written as short, numbered procedures so you can follow them while the customer is waiting. Use the **search box** at the top to filter by any word (try `payment`, `cancel`, `coupon`, `report`) or jump straight to a topic from **Contents**.

| Role | How you sign in | What you do |
| --- | --- | --- |
| Owner | Sign-in page → Role **Owner** → the owner password | Everything: orders, catalogue, prices, stock, coupons, staff accounts, reports, customer messages, community, settings. |
| Salesperson | Sign-in page → Role **Salesperson** → your own username and password | Handle orders and customers. Which screens you see is set by the Owner for your account (see *Permissions*). |
| Dispatch rider | Sign-in page → Role **Dispatch rider** → the rider password | See batched delivery orders and mark an order delivered once the customer has received it. |

> **Good to know:** If a page shows **403 / not allowed**, your account does not have that permission. Nothing is broken: ask the Owner to switch the permission on, or hand the task to someone who has it.

Sections marked **Owner only** are hidden from salesperson accounts. Procedures show the exact button or menu names you will see on screen, in **bold**.


## Running the site: the daily routine

*A simple opening, during-the-day and closing routine that keeps orders, stock and money consistent.*

**Opening checklist (first 10 minutes)**

1. Sign in with **your own named account**. Never share a login, and sign out on shared devices.
2. Open the **Order desk** (Owner: *Owner desk / overview*; Salesperson: *Order operations*). Read the shop status card: **Shop is open** means customers can place orders.
3. Turn on **alerts on this device** (*Enable owner alerts* / *Enable alerts on this device*) and allow notifications when the browser asks. You are then pinged the moment a new order arrives.
4. Open the **Live order stream**. Sort by *Oldest first* once to find anything left over from yesterday: orders still **Received**, **Confirmed** or **Prepared**.
5. Check which orders are **Awaiting payment verification**. Match each one against the business bank account or POS and verify those that have arrived (see *Payments and verification*).
6. Owner only: look at **Inventory summary** for low-stock items, and at the **abandoned carts** note on the dashboard.

**During the day: the order loop**

1. A new order alert arrives → open the order from the stream.
2. Check the items, the delivery zone or pickup choice, the customer's contact details and any processing methods ticked on an item.
3. Verify the payment in the bank/POS, then press **Verify payment, confirm order**.
4. Move the order along: **Prepared** → **Out for delivery** (delivery) or **Ready for pickup** (pickup) → **Delivered** or **Picked up**.
5. Reply to complaints and customer questions as they appear (see *Complaints and customer care*).

**Closing checklist**

1. Clear the stream: every order today should be **Delivered**, **Picked up**, **Cancelled**, or have a clear next step written in a note for the next shift.
2. Record any farm-counter sales you have not yet entered (*Record in-person sale*) so stock and reports are correct.
3. Make sure every cancellation has a reason selected.
4. Owner only: if you will not take orders overnight, switch the shop to **closed** from the shop status card and say when you reopen.
5. Sign out.

**Weekly and monthly (Owner)**

- Weekly: generate the **Sales report** (*Last 7 days*) and the **Inventory summary**; compare cancellations in the **Order summary**; restock and update stock counts.
- Weekly: review open complaints, reviews awaiting a response, and community reports.
- Monthly: generate the **Sales report** for *This month*, check coupon usage, review staff permissions and the **Staff report**, deactivate accounts that are no longer needed.

> **Tip:** The habit that prevents most problems: **verify money first, then change the status, then write down anything unusual.**


## Signing in, roles and permissions

*How to sign in, what each permission unlocks, and what to do when something is blocked.*

**Signing in**

1. Open the staff sign-in page (`/admin/login`).
2. Choose your **Role**. Salespeople enter their **username** and password; the Owner and the rider enter the shared role password.
3. If sign-in fails, check the Role first (a salesperson using the *Owner* role will always fail), then the username. Ask the Owner to **reset your password** if you cannot get in.
4. Use **Sign out** (top right of your desk) when you finish, especially on shared devices.

| Permission | What it lets a salesperson do |
| --- | --- |
| View the live order stream | Open **Live order stream** and see incoming website orders. |
| View customer contact and delivery details | See customer names, phone numbers and addresses. Without it you see only order contents. |
| Verify incoming POS / bank transfers | Press **Verify payment, confirm order** after the money is in the account. |
| Change order status | Move orders through the full status list and cancel with a reason. |
| Record weigh-ins on legacy orders | Use **Record actual weights** on older weight-priced orders. |
| Open and print customer receipts | Open and print a customer receipt. |
| View final customer balances/refunds on legacy settlement receipts | See the balance or refund amounts on a legacy settlement receipt. |
| View customer complaints | Open the complaints queue and read each complaint. |
| Manage complaints | Change a complaint's status and add internal notes. |
| Moderate community posts, reports and suggestions | Open **Community support**: reply as Beamers Farms, resolve reports, hide posts. |
| Record cash/POS orders at the farm counter | Use **Record in-person sale**. |
| View product stock summary | Open the **Inventory** page. |
| Generate sales reports / inventory summaries / order summaries | Create each report type for a chosen timeline. |
| Receive new-order push alerts while the shop is open | Get a notification on your device for each new order. |

> **Good to know:** Your **Actions** menu only lists what the Owner has allowed for your account. If a shortcut you expect is missing, the permission is off.

> **Careful:** Deactivating an account blocks that person on their **next request**. Do this the same day someone leaves or changes role.


## The order lifecycle

*The eight statuses, what each one means, and the rules that connect them.*

| Status | Meaning | Applies to |
| --- | --- | --- |
| Received | Order placed. Payment is not yet verified. Nothing is promised to the customer yet. | All orders |
| Confirmed | Payment verified in the bank/POS and the order accepted. | All orders |
| Prepared | The farm is picking, cleaning, processing and packing. | All orders |
| Out for delivery | Handed to a rider / dispatched to the delivery address. | Delivery orders only |
| Ready for pickup | Packed and waiting at the farm for the customer. | Pickup orders only |
| Delivered | The customer has received the order. | Delivery orders only |
| Picked up | The customer has collected the order at the farm. | Pickup orders only |
| Cancelled | Stopped. Stock is returned to inventory. A reason must be chosen. | All orders |

**Rules the system enforces**

- **No confirmation without verified payment.** Confirmed, Prepared, Out for delivery, Ready for pickup, Delivered and Picked up all require the payment to be verified first.
- **Verify payment while the order is Received** (or when you press **Verify payment, confirm order**, which verifies and confirms together). Payment can't be verified once fulfilment has begun.
- **Pickup and delivery are separate paths.** A pickup order goes Prepared → Ready for pickup → Picked up. A delivery order goes Prepared → Out for delivery → Delivered.
- **Cancelling returns the stock** of every item. Reopening a cancelled order takes the stock out again and is refused if there isn't enough.

> **Tip:** Customers can follow their order on the **Track order** page using their order reference, and may get push notifications when an order is confirmed or out for delivery. Keeping statuses accurate is how you keep customers informed.


## Handling an order, step by step

*The full procedure from the new-order alert to a completed order, for delivery and for pickup.*

**Step by step**

1. **Open the order.** Tap the new-order alert, or open the order from the **Live order stream** or the dashboard list. Each order has a reference like `#A1B2C3`.
2. **Read the order.** Check every line: product, quantity, and any **Processing** methods the customer ticked (for example *Cut into pieces, Vacuum sealed*). Check whether it is **delivery** (and which zone) or **farm pickup**.
3. **Check the money.** Look in the business bank account or POS for the exact amount due now (see *Payments and verification*). Do not rely on a screenshot.
4. **Verify and confirm.** Optionally type the **POS / bank reference**, then press **Verify payment, confirm order**. The status becomes *Confirmed* and the customer is notified where push or WhatsApp updates are enabled.
5. **Prepare.** Set the status to **Prepared** when picking and packing starts.
6. **Dispatch or hold for pickup.** Delivery: set **Out for delivery** (the rider sees it in their batch). Pickup: set **Ready for pickup**.
7. **Close it.** When the customer has the goods, set **Delivered** (delivery) or **Picked up** (pickup). The rider can also mark a delivery as delivered.
8. **If anything goes wrong**, do not delete or hide the order. Add a note, or cancel with the correct reason (see *Cancellations and stock*).

|  | Delivery order | Pickup order |
| --- | --- | --- |
| Fee | Fee of the chosen delivery zone is added at checkout | Free |
| Path | Received → Confirmed → Prepared → Out for delivery → Delivered | Received → Confirmed → Prepared → Ready for pickup → Picked up |
| Customer needs | A reachable phone and a correct address | To collect at the farm during opening hours |
| Typical delay cause | Wrong address, rider capacity | Customer not collecting |

> **Careful:** Only change a status when the real-world step has happened. Marking **Delivered** early tells the customer something untrue and hides a real problem.


## Payments and verification

*How customers pay, and the one rule that protects the farm's money.*

Customers choose how to pay at checkout. **Bank transfer** (manual transfer to the business account) is always available. **OPay checkout** appears only when the Owner has enabled the OPay integration. Either way, an order is created as **Received** with payment **not yet verified**.

**Verifying a bank or POS payment**

1. Open the order and note the **exact amount due now**.
2. Open the business bank app or POS statement and find a **completed credit** for that exact amount, ideally with the customer's name or order reference.
3. Back on the order, enter the **POS / bank reference** if you have it (optional but helpful).
4. Press **Verify payment, confirm order**. The payment status changes to *Payment verified* and the order becomes *Confirmed*.

**Never do this**

- Never confirm because a customer sent a **screenshot** or says they paid. Screenshots can be edited.
- Never confirm a *pending* or *reversed* credit. Wait until it is completed.
- Never confirm when the amount is **less** than the amount due. Ask the customer for the balance, or cancel with *Payment not received*.
- Never mark an order paid from the customer's browser return page alone. The system only trusts a verified credit (or a server-verified OPay callback).

> **Good to know:** Amounts are in Naira (₦). A customer who overpays should be flagged to the Owner so the extra can be refunded or credited and recorded.


## Cancellations, stock and reopening

*When to cancel, which reason to choose, and what cancelling does to stock.*

**Cancelling an order**

1. Open the order → **Update status**.
2. Set **Status** to **Cancelled**.
3. Pick the closest **Reason for cancelling**.
4. Press **Save status**. Stock is returned to the shelf automatically and the reason is stored.

| Reason | Use it when |
| --- | --- |
| Customer changed their mind | The customer decided not to buy. |
| Customer requested cancellation | The customer asked you to cancel an order they placed. |
| Payment not received | The money never arrived or was short, and the customer did not fix it. |
| Out of stock | An item can't be supplied. |
| Delivery address or zone problem | The address is outside the zones or can't be found. |
| Customer unreachable | You could not contact the customer after reasonable tries. |
| Duplicate order | The same order was placed twice. |
| Other | Anything else. Add a short factual note. |

**Good practice**

- The reason shows in the **Order summary** report, so choose the most honest one rather than *Other*.
- If a customer already paid, tell the Owner **before** cancelling so the refund is handled and recorded.
- To reopen a cancelled order, set a new status. It is refused if stock is no longer sufficient. Restock first.


## Weights, balances and refunds

*Older weight-priced orders, final amounts, and how balances and refunds are recorded.*

Some older orders were priced by weight. For these, the order page shows **Record actual weights**, and the final amount is calculated from the real weight.

**Recording actual weights (needs the weigh-in permission)**

1. Weigh each item when packing.
2. Open the order and find **Record actual weights**.
3. Enter the weight of each line and press **Save weights and calculate final amount** (salespeople: **Save legacy weigh-in**).
4. Check the final amount against what the customer paid. A difference becomes a **balance** to collect or a **refund** to pay.

**Balance or refund (Owner order page)**

1. Open **Balance or refund** on the order.
2. To collect a balance: enter **Amount received**, **Method**, **Reference / note**, then **Record balance received**.
3. To pay a refund: enter **Refund amount**, **Method**, **Reference / note**, then **Record refund paid**.
4. Both are saved under **Payment and adjustment records** on the customer's profile.

> **Careful:** Do not promise a refund, discount or credit that is not in this workflow. Escalate to the Owner.


## Live order stream, batching and riders

*Watching incoming orders, searching them, and how deliveries are grouped for riders.*

**Using the live order stream**

1. Open **Actions → Live order stream** (or the button on your desk).
2. Use **Search the stream** to find an order by reference (and by customer name or phone if you may view customer details).
3. Use **Sort by**: *Newest first* for new work, *Oldest first* to catch stragglers, *Highest value* to prioritise big orders.
4. Open any row to work on the order.

Delivery orders can be grouped into **dispatch batches** so a rider takes several nearby deliveries in one trip. Each batch has a number and a delivery time window (ETA). Riders sign in with the **Dispatch rider** role, see their batches and mark orders **delivered** once handed over.

**Owner: change how batches are formed**

1. Open **Live order stream** and find the batching settings.
2. Set **Batch interval (hours)**: how long orders are collected into one batch (between 0.25 and 24 hours; the default is 2).
3. Set **Batch delivery weight limit**: the most weight one batch should carry (default 50).
4. Press **Save batching**. New orders follow the new rules.

> **Tip:** Only orders in **Out for delivery** are shown to the rider for delivery. If a rider says they can't see an order, check its status and that it is a delivery order.


## Recording in-person (farm counter) sales

*How to record cash or POS sales made at the farm so stock and reports stay correct.*

Needs the **Record cash/POS orders at the farm counter** permission (Owner always has it).

**Record a sale**

1. Open **Actions → Record in-person sale**.
2. Add the products and quantities sold.
3. Enter **Buyer name** and **Buyer phone**.
4. Enter the **Cash/POS reference** (the POS slip number or a note such as *cash*).
5. Optional: set **Sale date and time** if you are recording a sale made earlier. Leave it empty to use the current time.
6. Press **Record sale in inventory**. Stock goes down immediately.

**Notes**

- In-person sales appear in reports as **farm-counter** sales, separate from website orders.
- Record sales the same day. Late entries cause stock counts to drift.
- If you record a sale by mistake, tell the Owner. Do not make an opposite sale to cancel it out.


## Customer accounts and privacy

*Reading customer information safely and what the account status labels mean.*

**Golden rules**

- Customer profiles are **private business records**. Verify who you are speaking to before discussing an order.
- Never copy phone numbers, addresses, emails, coupon or note data into personal chats or apps.
- Only see what you need. Without the *view customer details* permission you will see order contents but not contact details. That is by design.

| Account status | Meaning |
| --- | --- |
| Verified | The customer's email address has been confirmed with a code. |
| Unverified | The email is missing or still awaiting confirmation. |
| Private Community Profile | The customer has not opted into public community discovery. |

**Owner: finding and reading a customer**

1. Open **Actions → Manage customer accounts**.
2. Search by name, phone or email, or filter by **Segment**.
3. Open a customer. The profile shows contact information, account health, order history, payment and adjustment records, shopping behaviour, current or abandoned cart, recently viewed pages, preferences, engagement, support tickets, messages and notes.
4. Open the **Attached coupons** dropdown to see every coupon on this customer and whether it is active or paused.
5. Add a **private note** with only factual, work-related information, then **Save internal note**.

**Owner: account actions**

1. **Verification reminder**: nudge a customer to confirm their email.
2. **Reset password**: open the *Reset customer password* dropdown, enter a temporary password (at least 8 characters), press **Reset password**, and give it to the customer privately.
3. **Restrict community posting**: stops a customer posting in the community; the same button restores it.

> **Careful:** Report any suspected data exposure straight away (see *Security and escalation*). Do not wait until the end of the day.


## Complaints and customer care

*How to work the complaints queue so every complaint has an owner, a status and a record.*

Complaints arrive from customers through the site. Viewing needs **View customer complaints**; changing them needs **Manage complaints**.

| Status | Use it when |
| --- | --- |
| New | Nobody has looked at it yet. |
| Under Review | You are checking the order, contacting the customer or waiting for the Owner. |
| Resolved | The customer has an answer or a fix. |
| Closed | Finished and no further action is needed. |

**Handling a complaint**

1. Open **Actions → Manage complaints** (Owner: *Customer care queue*).
2. Search by complaint ID, order reference, customer name, phone, subject or status, or filter by status.
3. Open the complaint and read the customer's message and the **related order**.
4. Set the status to **Under Review** and write what you checked in **Internal notes**.
5. Contact the customer through the approved channel, then record what was said or promised.
6. When done, set **Resolved**, or **Closed** once everything is finished, and press **Save complaint**. The customer receives an account notice that the complaint was updated.

> **Careful:** Do not promise refunds, discounts or delivery times outside the approved workflow. Write what you found and escalate to the Owner.


## Community moderation

*Answering customers, handling reports and keeping the community safe. Needs the community permission for salespeople.*

Salespeople see **Community support** only when the Owner has granted **Moderate community posts, reports and suggestions**.

**Daily community routine**

1. Open **Actions → Community support**.
2. Read **No unanswered posts** / unanswered posts and answer with **Reply as Beamers Farms**. Replies from staff appear as official messages.
3. Open **reports**: read why a post was reported, then **Resolve** the report, or **Hide post** / **Hide reply** if it breaks the rules (abuse, private data, spam, scams).
4. Read **Ideas and feedback**, and pass useful suggestions to the Owner.
5. To jump to a specific post, use **Find post by ID** (every post shows `Post #id`).

**Owner: open or close the community**

1. In **Community support**, use the open/closed switch.
2. When closed, write the **Closed message** customers will see and press **Save message**.

> **Tip:** Official posts from the farm show as **Admin** and keep the green special-post style.


## Reports: generating, sharing and printing

*How to create each report, check it, and print or save it with or without the cover page.*

| Report | What it shows | Where |
| --- | --- | --- |
| Sales report | Headline figures, orders by status, a daily timeline, products sold and sales channels. | Actions → Sales report |
| Order summary | Orders in the period with status counts and cancellation reasons. | Actions → Order summary |
| Inventory summary | Stock on hand and activity in the period; can filter low stock. | Actions → Inventory summary |
| Staff report | Each salesperson's profile, status and optional action history. | Owner: Staff access → Generate staff report |

**Generate a report**

1. Open the report from **Actions**.
2. Choose the **Timeline** / **Order timeframe**: *Today, Last 7 days, Last 30 days, This month, This year, All time* or *Custom range* (then set **Start date** and **End date**).
3. Press **Generate report** / **Apply filters**.
4. Check the figures on screen. Read **How these figures are calculated** at the bottom of the Sales report if a number surprises you.

**Print or save as PDF**

1. Press **Print / Save as PDF**.
2. When asked, choose whether to **include the cover page**. The cover shows the reporting period, who prepared the report and the date. Choose *Cancel* to print without it.
3. On the staff report you are also asked whether to include the **logged actions**.
4. In the browser print window, choose **Save as PDF** or your printer, and keep **Background graphics** on so the cover prints in colour.

> **Careful:** Before you print, confirm the period, the status counts and who is allowed to see customer details. Reports are internal documents.

> **Good to know:** Dates use **Osogbo local time (WAT)**. A sale at 23:50 belongs to that day, not the next.


## Inventory and stock

*Reading stock, understanding how it moves, and what to do about low stock.*

**How stock moves**

- Stock is counted in **physical sale units** (for example birds, crates or kilograms, depending on the product).
- It **decreases** when an order is placed and when an in-person sale is recorded.
- It **increases** when an order is cancelled.
- The Owner changes **Stock on hand** on the product edit page when new stock arrives or a count shows a difference.

**Check stock (needs the inventory permission)**

1. Open **Actions → Inventory** (salespeople) or **Inventory summary** (Owner).
2. Choose the order timeframe and press **Apply filters**.
3. Use **Search product** to find one item, and the low-stock filter to list items near their alert level.

> **Careful:** If the screen and the shelf disagree, **do not edit orders to make the numbers match**. Tell the Owner. The count and the cause must both be recorded.


## Secure asset vault

*Sharing a private file, text or one-time link safely instead of using chat apps.*

**Store something in the vault**

1. Open **Actions → Secure drop** and press **New drop** at the top.
2. Choose **What are you dropping?** and add the **Text to share** or a **File or image**.
3. Optionally set a **password**, or choose a **One-time link**.
4. Press **Store in vault**. Copy the text or the link with **Copy text** / **Copy link**, then press **Done**.

> **Careful:** Send passwords through a different channel from the link. Remove vault items you no longer need.


## Alerts and notifications

*Getting new-order alerts on your phone or computer, and fixing alerts that don't arrive.*

**Turn alerts on**

1. On your desk, press **Enable alerts on this device** (Owner: **Enable owner alerts on this device**).
2. Allow notifications when the browser asks.
3. Do this on each device you use. **Disable alerts here** turns them off on that device.

**If alerts don't arrive**

- Check the browser still has notification permission for the site.
- Check you are not in a silent or battery-saver mode that blocks notifications.
- Salespeople: confirm **Receive new-order push alerts** is switched on for your account.
- Alerts are sent for new orders while the shop is open. When the shop is closed, check the stream manually.
- The alert is a prompt only. The **Live order stream** is always the source of truth.


## Troubleshooting: when something looks wrong

*The most common problems and the quickest safe fix.*

| Problem | Likely cause | What to do |
| --- | --- | --- |
| I can't confirm an order | Payment isn't verified yet. | Check the bank/POS, then use **Verify payment, confirm order**. |
| A page says 403 / not allowed | Your account lacks that permission. | Ask the Owner to enable it, or hand the task over. |
| I can't see a customer's phone or address | Customer details permission is off. | Ask the Owner. Do not ask a customer to repeat details in public. |
| A status option is missing or refused | Pickup and delivery use different statuses. | Use **Ready for pickup / Picked up** for pickup and **Out for delivery / Delivered** for delivery. |
| Can't reopen a cancelled order | Not enough stock. | Restock first, then reopen. |
| A customer says a coupon won't work | Expired, paused, used up, minimum spend or exclusion. | See *Why a coupon may not apply*. Offer an alternative only if the Owner agrees. |
| The report is empty | Wrong timeline or search term. | Check the **Timeline / Order timeframe**, dates and filters, then **Generate report** again. |
| Stock looks wrong | Late in-person sale or an unrecorded delivery. | Record missing sales, then tell the Owner about any remaining gap. |
| No new-order alert | Notifications blocked or shop closed. | See *Alerts and notifications*. Check the stream manually. |
| A message campaign shows many Skipped | Customers have no consent, contact or subscription. | Normal. Skipped is not an error. Failed is: open **Recent delivery issues**. |
| I can't sign in | Wrong role or username. | Choose the right **Role**; ask the Owner to reset your password. |

> **Good to know:** If the same problem repeats, write down the time, the page and what you pressed, and send it to the Owner. That detail makes a fix possible.


## Security and escalation

*How to protect the business and who to tell when something is wrong.*

**Everyday security**

- Use your **own** account only. Never share passwords or let someone work under your login.
- Sign out on shared or public devices.
- Never write customer data or passwords into personal chats, notes or screenshots.
- Never delete a record to hide a mistake. Use the correction workflow (cancel with a reason, add a note) so there is a true history.
- Be suspicious of urgent requests to change an account, bypass verification or send money.

| Escalate to the Owner immediately | Examples |
| --- | --- |
| Money | Payment mismatch, overpayment, a customer demanding a refund or discount, a missing credit. |
| Privacy / security | Suspected account compromise, a customer's data seen by the wrong person, lost phone with the desk signed in. |
| Stock | A discrepancy between the system and the shelf, spoiled or contaminated stock. |
| Delivery | A rider incident, a missed promise, a repeated address problem. |
| Behaviour | Abusive or threatening customer contact. |

> **Tip:** When you escalate, include: the order reference or customer ID, what happened, what you already did, and what you need decided.


## Glossary

*Plain-language meanings of the terms used on the desk.*

| Term | Meaning |
| --- | --- |
| Order reference | The short code on each order, such as `#A1B2C3`, used by customers and staff. |
| Verified payment | The amount due has been seen as a completed credit in the business bank/POS. |
| Amount due now | What the customer must pay now for the order, including any delivery fee. |
| Zone | A delivery area with its own fee. Farm pickup is the free option. |
| Processing method | An optional preparation request on an item, such as *Cut into pieces*. |
| Dispatch batch | A group of delivery orders taken by a rider in one trip, with a time window. |
| Stream | The live list of incoming website orders. |
| Skipped (message) | A customer could not be reached on a channel. Not an error. |
| Special / Admin post | An official community post from the farm, shown with the green style. |
| WAT | West Africa Time, the time zone used in all reports. |


## Customer reviews and moderation

The Owner manages customer reviews from **Owner desk → Reviews**. The review queue is intentionally compact: each card shows the star rating and review title, with its current status. Use the vertical **three-dot** menu on the card to open **Moderate review**.

1. Use **Filter by status** to find Pending, Approved or other review states. Use **Filter by stars** to narrow the queue to a 1–5 star rating. Both filters can be applied together; choose **Clear** to return to the full queue.
2. Open the review menu and choose **Moderate review** to see the customer's review text and moderation form.
3. Choose the correct publication status. Add an optional, respectful **Owner response** when a public reply is useful.
4. Select **Save moderation**. The customer may receive an account notice when their review status or response changes.
5. Close the dialog with **×** or **Cancel** without saving if you opened it by mistake.

**Review handling principles**

- Keep replies factual, courteous and free of private order or contact details.
- Do not approve a review merely because it is positive, or reject one merely because it is critical. Apply the same standards to all customers.
- Use the review's linked order details when checking a concern; do not expose internal order identifiers in a public response.
- The automatic publication setting is separate from manual moderation. Changing the setting affects future eligible submissions; existing reviews can still be moderated.

## Using compact menus and forms accessibly

- A vertical three-dot button opens actions for the item beside it. Use the visible action label rather than relying on the icon alone.
- Dialogs can be closed with their **×** or **Cancel** control. Check the dialog title before saving.
- On narrow screens, forms may stack fields vertically. Scroll through the complete form rather than expecting related fields to remain side by side.
- Labels sit above their fields; use the label text to confirm what a field expects. Do not enter sensitive customer details into a public note or response.
