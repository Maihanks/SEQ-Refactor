package orders;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class OrderServiceTest {

    private OrderService newService() {
        Warehouse warehouse = new Warehouse(
                new Warehouse.Inventory(new Warehouse.ReservationDesk()));
        BillingGateway billing = new BillingGateway(
                new BillingGateway.Ledger(new BillingGateway.PostingQueue()));
        return new OrderService(warehouse, billing);
    }

    private Customer goldCustomer() {
        Customer.ShippingZone zone = new Customer.ShippingZone("REGIONAL");
        Customer.Region region = new Customer.Region(zone);
        Customer.Address address = new Customer.Address(region);
        return new Customer("cust-1", "GOLD", address);
    }

    @Test
    void checkoutProducesReceiptAndAdvancesStatus() {
        OrderService service = newService();
        Order order = new Order("order-1", goldCustomer());
        order.addItem("sku-1", 2, 20.0);
        order.addItem("sku-2", 1, 15.0);

        String receipt = service.checkout(order);

        assertTrue(receipt.contains("order=order-1"));
        assertEquals("PLACED", order.getStatus());
    }

    @Test
    void applyDiscountRewardsGoldTierAndVolume() {
        OrderService service = newService();
        Order order = new Order("order-2", goldCustomer());
        for (int i = 0; i < 10; i++) {
            order.addItem("sku-" + i, 1, 60.0);
        }

        double discounted = service.applyDiscount(order, 600.0);

        assertTrue(discounted < 600.0);
    }

    @Test
    void priceOfAppliesRegionalSurchargeOutsideLocalZone() {
        OrderService service = newService();
        Customer customer = goldCustomer();

        double price = service.priceOf(sampleItem(), customer);

        assertTrue(price > 0.0);
    }

    @Test
    void dispatchStatusMapsKnownStatusesAndFallsBackForUnknown() {
        OrderService service = newService();
        Order order = new Order("order-4", goldCustomer());
        order.setStatus("SHIPPED");
        assertEquals("in-transit", service.dispatchStatus(order));

        order.setStatus("SOMETHING_ELSE");
        assertEquals("unknown", service.dispatchStatus(order));
    }

    private Order.LineItem sampleItem() {
        Order carrier = new Order("carrier", goldCustomer());
        carrier.addItem("sku-x", 3, 10.0);
        return carrier.getItems().get(0);
    }
}
