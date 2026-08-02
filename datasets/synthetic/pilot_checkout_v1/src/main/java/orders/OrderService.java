package orders;

/**
 * Injected-smell subject for the pilot_checkout_v1 synthetic module
 * (datasets/synthetic/pilot_checkout_v1/manifest.yaml).
 *
 * This class is DELIBERATELY a God Class: it owns pricing, discounting,
 * inventory reservation, billing, notification, and status dispatch, which
 * is what makes it a structural prerequisite of every method-level smell
 * declared in the manifest (s2..s7). Do not "clean it up" -- the smells are
 * the fixture, not a defect.
 */
public class OrderService {

    private final Warehouse warehouse;
    private final BillingGateway billingGateway;

    public OrderService(Warehouse warehouse, BillingGateway billingGateway) {
        this.warehouse = warehouse;
        this.billingGateway = billingGateway;
    }

    // --- s2: LongMethod --------------------------------------------------
    public String checkout(Order order) {
        if (order == null) {
            throw new IllegalArgumentException("order must not be null");
        }
        double subtotal = 0.0;
        for (Order.LineItem item : order.getItems()) {
            subtotal += item.getUnitPrice() * item.getQuantity();
        }
        double discounted = applyDiscount(order, subtotal);
        double shipping = 0.0;
        String zone = order.getCustomer().getAddress().getRegion().getShippingZone().getCode();
        if ("LOCAL".equals(zone)) {
            shipping = 2.5;
        } else if ("REGIONAL".equals(zone)) {
            shipping = 6.0;
        } else {
            shipping = 12.0;
        }
        double total = discounted + shipping;
        StringBuilder receipt = new StringBuilder();
        receipt.append("order=").append(order.getId());
        receipt.append(";subtotal=").append(subtotal);
        receipt.append(";discounted=").append(discounted);
        receipt.append(";shipping=").append(shipping);
        receipt.append(";total=").append(total);
        for (Order.LineItem item : order.getItems()) {
            notifyWarehouse(item.getSku(), item.getQuantity());
        }
        notifyBilling(order.getId(), total);
        order.setStatus("PLACED");
        dispatchStatus(order);
        return receipt.toString();
    }

    // --- s3: LongMethod ----------------------------------------------------
    public double applyDiscount(Order order, double subtotal) {
        double rate = 0.0;
        String tier = order.getCustomer().getTier();
        if ("PLATINUM".equals(tier)) {
            rate = 0.15;
        } else if ("GOLD".equals(tier)) {
            rate = 0.10;
        } else {
            rate = 0.0;
        }
        int itemCount = order.getItems().size();
        if (itemCount >= 10) {
            rate += 0.05;
        } else if (itemCount >= 5) {
            rate += 0.02;
        }
        if (subtotal > 500.0) {
            rate += 0.03;
        }
        if (rate > 0.30) {
            rate = 0.30;
        }
        double discount = subtotal * rate;
        double result = subtotal - discount;
        if (result < 0.0) {
            result = 0.0;
        }
        return result;
    }

    // --- s4: LongMethod ------------------------------------------------
    public double priceOf(Order.LineItem item, Customer customer) {
        double base = item.getUnitPrice() * item.getQuantity();
        double loyaltyAdjustment = 0.0;
        if ("PLATINUM".equals(customer.getTier())) {
            loyaltyAdjustment = base * 0.02;
        } else if ("GOLD".equals(customer.getTier())) {
            loyaltyAdjustment = base * 0.01;
        }
        double regionalSurcharge = 0.0;
        String code = customer.getAddress().getRegion().getShippingZone().getCode();
        if (!"LOCAL".equals(code)) {
            regionalSurcharge = base * 0.015;
        }
        return base - loyaltyAdjustment + regionalSurcharge;
    }

    // --- s5: MessageChains ---------------------------------------------
    public String notifyWarehouse(String sku, int quantity) {
        return warehouse.getInventory().getReservationDesk().reserve(sku, quantity);
    }

    // --- s6: MessageChains -----------------------------------------------
    public String notifyBilling(String orderId, double amount) {
        return billingGateway.getLedger().getPostingQueue().post(orderId, amount);
    }

    // --- s7: BigSwitch ---------------------------------------------------
    public String dispatchStatus(Order order) {
        switch (order.getStatus()) {
            case "NEW":
                return "awaiting-checkout";
            case "PLACED":
                return "awaiting-fulfilment";
            case "RESERVED":
                return "awaiting-billing";
            case "BILLED":
                return "awaiting-shipment";
            case "SHIPPED":
                return "in-transit";
            case "DELIVERED":
                return "complete";
            case "CANCELLED":
                return "cancelled";
            case "REFUNDED":
                return "refunded";
            default:
                return "unknown";
        }
    }
}
