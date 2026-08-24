package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class LeafClass4Test {

    @Test
    void leafSwitchBehaves() {
        LeafClass4 subject = new LeafClass4();
        assertEquals("v2", subject.leafSwitch(2));
    }

}
