package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class LeafClass1Test {

    @Test
    void leafSwitchBehaves() {
        LeafClass1 subject = new LeafClass1();
        assertEquals("two", subject.leafSwitch(2));
    }

}
