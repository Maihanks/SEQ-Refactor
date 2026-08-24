package synth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class LeafClass3Test {

    @Test
    void leafSwitchBehaves() {
        LeafClass3 subject = new LeafClass3();
        assertEquals("v2", subject.leafSwitch(2));
    }

}
