package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class LeafClass0Test {

    @Test
    void leafSwitchBehaves() {
        LeafClass0 subject = new LeafClass0();
        assertEquals("two", subject.leafSwitch(2));
    }

}
