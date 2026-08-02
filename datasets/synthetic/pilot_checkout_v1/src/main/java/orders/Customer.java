package orders;

public class Customer {
    private final String id;
    private final String tier; // "STANDARD" | "GOLD" | "PLATINUM"
    private final Address address;

    public Customer(String id, String tier, Address address) {
        this.id = id;
        this.tier = tier;
        this.address = address;
    }

    public String getId() {
        return id;
    }

    public String getTier() {
        return tier;
    }

    public Address getAddress() {
        return address;
    }

    public static class Address {
        private final Region region;

        public Address(Region region) {
            this.region = region;
        }

        public Region getRegion() {
            return region;
        }
    }

    public static class Region {
        private final ShippingZone shippingZone;

        public Region(ShippingZone shippingZone) {
            this.shippingZone = shippingZone;
        }

        public ShippingZone getShippingZone() {
            return shippingZone;
        }
    }

    public static class ShippingZone {
        private final String code;

        public ShippingZone(String code) {
            this.code = code;
        }

        public String getCode() {
            return code;
        }
    }
}
