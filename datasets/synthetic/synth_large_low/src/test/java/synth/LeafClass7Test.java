package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class LeafClass7Test {

    @Test
    void leafSwitchBehaves() {
        LeafClass7 subject = new LeafClass7();
        assertEquals("v2", subject.leafSwitch(2));
    }

}
