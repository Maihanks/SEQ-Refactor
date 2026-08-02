package orders;

public class Warehouse {
    private final Inventory inventory;

    public Warehouse(Inventory inventory) {
        this.inventory = inventory;
    }

    public Inventory getInventory() {
        return inventory;
    }

    public static class Inventory {
        private final ReservationDesk reservationDesk;

        public Inventory(ReservationDesk reservationDesk) {
            this.reservationDesk = reservationDesk;
        }

        public ReservationDesk getReservationDesk() {
            return reservationDesk;
        }
    }

    public static class ReservationDesk {
        public String reserve(String sku, int quantity) {
            return "RESERVED:" + sku + ":" + quantity;
        }
    }
}
