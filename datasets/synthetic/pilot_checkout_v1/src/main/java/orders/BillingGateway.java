package orders;

public class BillingGateway {
    private final Ledger ledger;

    public BillingGateway(Ledger ledger) {
        this.ledger = ledger;
    }

    public Ledger getLedger() {
        return ledger;
    }

    public static class Ledger {
        private final PostingQueue postingQueue;

        public Ledger(PostingQueue postingQueue) {
            this.postingQueue = postingQueue;
        }

        public PostingQueue getPostingQueue() {
            return postingQueue;
        }
    }

    public static class PostingQueue {
        public String post(String orderId, double amount) {
            return "POSTED:" + orderId + ":" + amount;
        }
    }
}
