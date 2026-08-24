package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class LeafClass5Test {

    @Test
    void leafSwitchBehaves() {
        LeafClass5 subject = new LeafClass5();
        assertEquals("v2", subject.leafSwitch(2));
    }

}
